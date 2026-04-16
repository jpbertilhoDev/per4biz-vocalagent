# Error Matrix — Per4Biz

**Documento operacional** — como o sistema reage a cada tipo de erro. Referência obrigatória durante implementação.

---

## 1. Política geral de erros

Três princípios não-negociáveis:

1. **Nunca expor stacktraces ou mensagens internas ao utilizador** — logar internamente (Sentry/Axiom), mostrar mensagem amigável em PT-PT.
2. **Sempre oferecer uma ação de recuperação** — "Tentar novamente", "Ir para modo offline", "Re-autenticar", nunca um beco sem saída.
3. **Distinguir erros recuperáveis (retry automático) de não-recuperáveis (exige ação do user)** — retry automático só faz sentido para falhas transitórias.

### Taxonomia de severidade

| Severidade | Comportamento | Onde loga | User vê? |
|---|---|---|---|
| **INFO** | Operação normal | Axiom | Não |
| **WARN** | Situação anormal mas recuperável | Axiom + Sentry breadcrumb | Às vezes (toast informativo) |
| **ERROR** | Falha que bloqueia ação do user | Sentry event | Sim (mensagem + recuperação) |
| **CRITICAL** | Falha que afeta segurança ou integridade | Sentry + PagerDuty | Depende (logout forçado se auth) |

---

## 2. Matriz — Google APIs (Gmail / Calendar / People)

| Código HTTP | Causa típica | Comportamento do sistema | Mensagem PT-PT ao user |
|---|---|---|---|
| **401 Unauthorized** | Access token expirado ou inválido | Retry 1× com `refresh_token`; se falhar → logout da conta + forçar re-OAuth | "A tua sessão expirou. Entra de novo com a Google." |
| **403 Forbidden** (scope missing) | Scope não foi concedido (user autorizou só parcialmente) | Pedir re-autorização incremental com scope em falta | "Precisamos de mais permissões para esta ação. Autorizar?" |
| **403 Forbidden** (access revoked) | User revogou acesso em myaccount.google.com | Apagar row `google_accounts` + forçar re-OAuth | "Revogaste acesso ao Per4Biz na Google. Volta a ligar a conta." |
| **404 Not Found** | Email/evento/contact apagado entre cache e fetch | Remover do cache local + refresh silencioso | Nenhuma (se listagem) / "Este email já não existe" (se aberto direto) |
| **429 Too Many Requests** | Quota Gmail excedida (raro para 1 user) OU rate limit interno | Backoff exponencial: 1s → 2s → 4s → 8s (máx 4×); depois cair no cache | "Muitos pedidos. A aguardar antes de tentar novamente…" |
| **500 / 502 / 503 / 504** | Serviço Google temporariamente indisponível | Retry 3× com backoff; se falhar → cache local com banner offline | "O Gmail está temporariamente em baixo. A mostrar emails guardados." |
| **Network error** (timeout, DNS) | Sem conectividade | Modo offline automático; banner permanente; retry em background ao voltar | "Sem ligação. A ver dados guardados." |
| **OAuth `invalid_grant`** | Refresh token inválido ou revogado | `DELETE google_accounts` cascata + redirect para re-login | "Precisamos que entres de novo. A tua sessão anterior expirou." |
| **OAuth `invalid_client`** | Credentials OAuth da app inválidas (config error) | CRITICAL — Sentry alert imediato; app mostra página de manutenção | "Há um problema no Per4Biz. Já estamos a resolver." |

### Backoff exponencial — implementação padrão

```python
async def retry_with_backoff(fn, max_attempts=4, base_delay=1.0):
    for attempt in range(max_attempts):
        try:
            return await fn()
        except (httpx.HTTPError, GoogleAPIError) as e:
            if attempt == max_attempts - 1 or not is_retryable(e):
                raise
            await asyncio.sleep(base_delay * (2 ** attempt))
```

---

## 3. Matriz — Voice Agent (STT + LLM + TTS)

| Cenário | Causa técnica | Comportamento | Mensagem / UX |
|---|---|---|---|
| **STT não reconhece fala** | Ruído, sotaque forte, idioma errado | Mostra "Não percebi"; mantém microfone ativo +5s; permite re-gravar | Onda vira vermelha; texto "Não percebi — tenta de novo" |
| **STT permission denied** | User bloqueou mic no browser | Fallback total para input de texto | Modal: "Para ditar, permite o microfone nas definições do browser" + botão "Escrever em vez disso" |
| **Groq Whisper 5xx / timeout > 5s** | Groq indisponível ou lento | Fallback para OpenAI Whisper API | Transparente para o user; toast subtil "A usar modo alternativo" |
| **Groq API quota / rate limit** | Free tier exausto | Fallback OpenAI Whisper | Banner: "Voz a funcionar em modo degradado" |
| **Claude 3.5 timeout > 15s** | Anthropic congestionado | Cancelar request; oferecer retry ou modo manual | Spinner desaparece; toast: "Demorou muito. Tenta de novo ou escreve manualmente." |
| **Claude API error (401/403)** | Key inválida ou conta sem créditos | Desativar feature LLM; Settings banner amarelo | "O copiloto IA está temporariamente indisponível — podes escrever emails manualmente." |
| **Claude rate limit (429)** | Spike de pedidos | Retry com backoff; fallback Groq Llama para drafts | Transparente; latência ligeiramente maior |
| **ElevenLabs 5xx / timeout** | Provider indisponível | Fallback Web Speech Synthesis API (nativa browser) | Toast: "Voz em modo alternativo" |
| **ElevenLabs character quota exceeded** | Mensal estourado | Fallback Web Speech; alerta admin | Transparente ao user |
| **LLM gera resposta ofensiva / inadequada** | Hallucination | Guardrail prompt + manual review; NUNCA enviar sem user approval (CON-015) | AC-E5.US1 cobre: user SEMPRE vê draft antes de enviar |
| **Transcrição retorna string vazia** | User carregou no botão sem falar | UI mostra "Não ouvi nada — tenta de novo" sem consumir pipeline LLM/TTS | — |

### Pipeline de fallback (cascata)

```
STT:    Groq Whisper v3 → OpenAI Whisper → Web Speech API (last resort)
LLM:    Claude 3.5 Sonnet → Groq Llama 3.3 70B → GPT-4o-mini
TTS:    ElevenLabs Multilingual v2 → Web Speech Synthesis API
```

---

## 4. Matriz — Envio de email

| Cenário | Causa | Comportamento | UX recovery |
|---|---|---|---|
| **Gmail send 5xx** | API temporariamente em baixo | Retry 3× com backoff; se falhar → guarda como draft local (outbox IndexedDB) | Toast: "Vou enviar quando voltares online" + ícone de relógio no draft |
| **Draft sem destinatário** (campo `to` vazio) | Validação client-side falhou | `POST /emails/send` devolve `422`; highlight do campo + impede submit | "Falta o destinatário" em vermelho junto ao campo |
| **Email > 25 MB** (limite Gmail) | User anexou muito | Bloqueia criação do draft antes de chamar API | Toast: "Email muito grande — o Gmail aceita até 25 MB" |
| **Conta removida durante draft aberto** | User apagou a conta em outra tab | Descarta draft + redirect home | Modal: "A conta foi removida. O rascunho foi descartado." |
| **Destinatário inválido (RFC 5322)** | Email mal formado | Validação client-side antes de enviar | Highlight: "Email inválido" |
| **Draft enviado 2× (double-tap)** | User tocou 2× rápido no botão Enviar | `draft_responses.status = 'sent'` como guard; 2ª tentativa é no-op | Silent — não mostrar erro confuso |
| **User offline ao tentar enviar** | Sem rede | Guarda em outbox IndexedDB; Background Sync API envia ao voltar online | Banner: "Será enviado quando voltares online" |

---

## 5. Edge cases — Multi-conta

| Edge case | Situação | Comportamento esperado |
|---|---|---|
| **Token expira só na conta 2** | Conta 2 inativa > 1h sem refresh, conta 1 ativa | Apenas conta 2 mostra badge "Re-autenticar"; conta 1 funciona normal |
| **Google revoga acesso à conta 1** | User revogou em myaccount.google.com | Próxima sync → 401 `invalid_grant` → apaga `google_accounts` + notif ao user |
| **Inbox unificada com 0 emails em ambas** | Ambas contas vazias | Empty state único; sem crash; sem duplicate empty state por conta |
| **Contato com mesmo nome em 2 contas** | "João Silva" existe em Contacts da conta A e B | Pesquisa devolve ambos com label da conta de origem |
| **Evento criado com convidado sem email** | Contact tem só telefone | Evento criado sem convidado; warning "Este contacto não tem email — não foi convidado" |
| **Switching conta durante composer aberto** | User muda de conta enquanto dita | Modal: "Descartar rascunho da conta A ou mover para conta B?" |
| **Inbox unificada: email aparece 2× (thread cross-account)** | Mesmo thread em 2 contas (mail list) | Deduplicar por `thread_id` quando possível; fallback mostrar ambos com indicador |

---

## 6. Edge cases — OAuth / Sessão

| Edge case | Situação | Comportamento |
|---|---|---|
| **CSRF attack no callback** | Atacante forja callback com `code` mas `state` inválido | FastAPI retorna `400 Invalid state`; log WARN em Axiom; nenhuma sessão criada |
| **Callback recebido 2× (duplicate tab)** | User carregou 2 tabs de OAuth | 1ª request cria conta; 2ª recebe `409 Account already linked` |
| **User fecha browser durante OAuth** | Abandono a meio | Sem efeito — nada foi criado na BD; state JWT expira em 10 min |
| **Clock skew entre client e Google** | Relógio device errado | `id_token` fail (iat/exp); mostrar "Verifica a data/hora do teu device" |
| **User tem 2FA desafio Google** | Account recovery em curso | Google bloqueia OAuth com erro específico; mostrar "Completa verificação Google e tenta de novo" |

---

## 7. Matriz — PWA / Browser / Offline

| Cenário | Comportamento |
|---|---|
| **Service Worker falha a instalar** | App funciona sem offline cache; Sentry log |
| **LocalStorage quota exceeded** | Limpar caches não críticos; toast "A limpar espaço…" |
| **User desinstala PWA** | Sessão perdida; próximo login pede tudo de novo (esperado) |
| **IndexedDB corrompida** | Limpar + reforçar cache do servidor; Sentry log |
| **Push notification permission denied** | Settings mostra "Notificações desligadas" + instruções para ativar |
| **iOS 16.4+ mas PWA não instalado** | Web Push não funciona; banner "Instala para receber notificações" |
| **Idle > 24h em background** | iOS Safari pode limpar cache — refresh silencioso ao voltar |

---

## 8. Padrões de mensagens user-facing (PT-PT)

**Estilo:**
- **Directo** — sem jargão técnico ("Falha HTTP 502" ❌ → "O Gmail está temporariamente em baixo" ✅)
- **Empático** — não culpar o user ("Cometeste um erro" ❌ → "Algo correu mal — tenta de novo" ✅)
- **Acionável** — sempre sugerir próximo passo
- **Breve** — máximo 2 linhas no toast; modal pode ser um pouco mais longo
- **PT-PT** — "tu" (informal) em toda a app; nunca "você" formal

### Templates

| Situação | Template |
|---|---|
| Ação vai ser tentada de novo | "A tentar novamente…" |
| Falha recuperável | "Algo correu mal. [Tentar novamente]" |
| Falha permanente | "Não conseguimos [ação]. [Alternativa/Suporte]" |
| Ação destrutiva | "Tens a certeza? Esta ação não pode ser desfeita." |
| Sucesso | "Feito." / "Enviado." / "Apagado." (verbos curtos) |
| Offline | "Sem ligação. A mostrar dados guardados." |

---

## 9. Como instrumentar

Em cada `catch` / `except`:

```python
# Backend (Python)
try:
    result = await gmail_api.list_messages(account_id)
except GoogleAPIError as e:
    logger.error(
        "gmail_list_failed",
        extra={"user_id": user_id, "account_id": account_id, "google_code": e.code}
        # NUNCA extra={"email_body": ..., "token": ...}
    )
    sentry_sdk.capture_exception(e)
    raise HTTPException(502, detail="Gmail temporariamente indisponível")
```

```typescript
// Frontend (TypeScript)
try {
  await emailsApi.send(draftId);
  toast.success("Enviado.");
} catch (err) {
  if (err.code === "OFFLINE") {
    await outbox.enqueue(draftId);
    toast.info("Sem ligação — será enviado depois.");
  } else {
    toast.error("Não conseguimos enviar. [Tentar novamente]");
    Sentry.captureException(err);
  }
}
```

Ver [LOGGING-POLICY.md](LOGGING-POLICY.md) para a política completa.
