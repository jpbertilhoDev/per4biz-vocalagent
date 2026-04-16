# Constraints, Assumptions & Out of Scope — Per4Biz

**Documento formal de limites do sistema.** Usar em conjunto com o [PRD mestre](../01-prd/PRD-MASTER.md) e o [Ultraplan](../02-ultraplan/ULTRAPLAN-tecnico.md).

---

## 1. Constraints (Restrições não-negociáveis)

Limites que o sistema **tem de** respeitar. Violar uma constraint significa ou ilegalidade, ou o produto não funciona.

| ID | Restrição | Origem | Impacto no design |
|---|---|---|---|
| **CON-001** | A app nunca armazena passwords Google — apenas OAuth 2.0 tokens | Google ToS + GDPR | Arquitetura OAuth obrigatória; não há sign-up com password próprio |
| **CON-002** | Google Gmail API quota: 1 bilhão quota units/dia (free tier); cada email fetch = ~5 units | [Google API Quotas](https://developers.google.com/gmail/api/reference/quota) | Irrelevante para uso 1-10 users; monitorizar via Upstash Redis rate-limit interno 60 req/min/user |
| **CON-003** | Web browser não dá acesso a microfone sem permissão explícita (cada sessão iOS) | W3C Media Capture + iOS Safari policy | Push-to-talk após permissão; fallback textual se negado |
| **CON-004** | Web Speech API não existe em Firefox; iOS < 16.4 sem Web Push | Browser compatibility matrix | Groq Whisper (cloud) como principal; Firefox users usam STT cloud; Web Push desligado em iOS < 16.4 |
| **CON-005** | Gmail scopes restricted (`gmail.send`, `gmail.modify`) exigem CASA Tier 2 Letter of Assessment para passar de modo "testing" | [Google OAuth Verification](https://support.google.com/cloud/answer/9110914) | Beta fechado (≤ 100 users) em modo "testing"; CASA obrigatório para production pública; €8-15k + 6-10 semanas |
| **CON-006** | `refresh_token` Google expira se não usado > 6 meses, OU se user revoga acesso em myaccount.google.com | [Google OAuth Docs](https://developers.google.com/identity/protocols/oauth2) | Detectar `invalid_grant` → forçar re-login gracefully; nunca guardar tokens > 6 meses sem uso |
| **CON-007** | iOS Safari em modo standalone PWA perde cookies quando o sistema limpa storage | Apple WebKit policy | Teste físico iOS semanal; fallback de refresh token em IndexedDB encriptado (ADR a escrever) |
| **CON-008** | Supabase RLS em todas as tabelas user-scoped — FastAPI usa `service_role` mas tem de aplicar `user_id` explícito em cada query | Multi-tenant security | Code review obrigatório para qualquer query sem `WHERE user_id` |
| **CON-009** | Corpo de email **nunca** persistido > 24h (`email_cache.body_cached`) | GDPR minimização + ADR-005 | Cron Supabase Edge Function diário; re-fetch ao Gmail se user relê email antigo |
| **CON-010** | Dados dos utilizadores UE residem em região EU (Supabase Paris ou Frankfurt; Fly.io Madrid) | GDPR residência de dados | Nunca us-east, us-west; SCCs aceitáveis apenas para Google/Anthropic/Groq/ElevenLabs (providers US com DPA assinado) |
| **CON-011** | Refresh tokens cifrados AES-256-GCM antes de persistir; chave mestra em Fly.io Secrets | Security baseline interno | Coluna `refresh_token_encrypted BYTEA` + `key_version` para rotação trimestral sem downtime |
| **CON-012** | mTLS / shared secret entre Next.js BFF e FastAPI via header `X-Internal-Auth` | Defense in depth | FastAPI rejeita requests sem header válido; secret em env var, rotação trimestral |
| **CON-013** | Cap de 200 interações vocais/dia/utilizador (STT+LLM+TTS) | Controlo de custo APIs | Upstash Redis sliding window; 201ª chamada → `429` com "Limite diário atingido" |
| **CON-014** | Utilizadores recebem consent screen GDPR no 1º login — checkbox obrigatório | GDPR Art. 6(1)(a) | Tabela `consent_log (user_id, version_id, timestamp, ip_hash)` — imutável, append-only |
| **CON-015** | Confirmação obrigatória antes de `POST /emails/send` — nunca envio automático | Risco de reputação + AC-E5.US4 | Guardrail no backend: rejeita envios sem `draft_responses.status='approved'` |

---

## 2. Assumptions (Pressupostos)

Factos que assumimos verdadeiros para o design do sistema funcionar. Se falharem, o produto degrada.

| ID | Pressuposto | Risco se falso | Plano B |
|---|---|---|---|
| **ASM-001** | O utilizador tem conta Google ativa com Gmail habilitado | App inutilizável — login falha | Mensagem clara "Precisas de conta Google" |
| **ASM-002** | Utilizador tem ligação à internet para OAuth inicial + sync | Sem login possível | Modo offline só lê cache; login exige online |
| **ASM-003** | Utilizador fala PT-PT (Portugal) como idioma principal | STT/TTS/LLM em idioma errado | Configurável em Settings; default pt-PT; i18n no V2 |
| **ASM-004** | Google Cloud Console do dev tem Gmail API + Calendar API + People API habilitadas | 403 Forbidden em todos os endpoints | Checklist Sprint 0 Dia 1 |
| **ASM-005** | API keys (Anthropic, Groq, ElevenLabs) válidas com créditos disponíveis | Pipeline de voz / drafts indisponível | Fallback em cascata: Claude → Groq Llama → OpenAI (se key disponível) |
| **ASM-006** | Fly.io Madrid suporta HTTPS/TLS 1.3 e WebSockets | Streaming LLM/TTS pode falhar | Fly.io há > 3 anos comprovadamente; probabilidade baixa |
| **ASM-007** | Utilizador usa device moderno (≤ 5 anos) com iOS ≥ 16.4 ou Android ≥ 10 | PWA features (Web Push, Speech API) indisponíveis | Feature detection + degradação graciosa; banner "funcionalidade indisponível neste device" |
| **ASM-008** | Conta Google do utilizador não está sujeita a Advanced Protection Program (tokens revogados todas as 24h) | App obriga re-login diário | Mensagem clara explicando + alternativa (workspace account sem APP) |
| **ASM-009** | Utilizador aceita política de privacidade e consent para processar emails via LLM cloud | Se rejeita → app não funciona | Sem dark pattern — recusar consent = ecrã explicativo + link para alternativa local (não existe na V1) |
| **ASM-010** | Latência de rede Lisboa → Fly.io Madrid < 30ms em 4G/5G | Pipeline voz > 4s inviabiliza UX | Medido em POC S0; se falhar, avaliar Fly.io `cdg` (Paris) ou edge computing |

---

## 3. Out of Scope (Fora do âmbito V1)

Funcionalidades **explicitamente excluídas** do MVP. Incluí-las causaria scope creep e comprometeria a entrega em 13 semanas.

| ID | Funcionalidade fora do âmbito | Justificação | Versão-alvo |
|---|---|---|---|
| **OOS-001** | Suporte a contas de email não-Google (Outlook, Yahoo, IMAP genérico) | Cada provider requer integração separada; foco Google-first | V2 (se houver procura) |
| **OOS-002** | Aplicação nativa iOS / Android (App Store / Play Store) | PWA cobre 95% do caso de uso; submissões store são trabalho separado | V3 |
| **OOS-003** | Sistema multi-utilizador em instância partilhada (SaaS com login de empresa) | Arquitetura single-tenant por utilizador; refactor major para tenancy | V2 |
| **OOS-004** | Gestão completa de anexos (upload, download, preview) | Requer Supabase Storage signed URLs + parser MIME complexo + considerações privacidade | V1.x / V2 |
| **OOS-005** | Integração com Google Drive (ler/partilhar docs) | Fora do core email+calendar+contacts | V2 |
| **OOS-006** | Wake-word passivo ("Ei Per4" sempre à escuta) | Limitações iOS PWA + impacto bateria + implicações GDPR | V2 (via Porcupine Web SDK) |
| **OOS-007** | Dashboard de analytics e relatórios de produtividade | Valor mas não essencial para loop mínimo V1 | V2 |
| **OOS-008** | Mais de 2 contas Google simultâneas na UI | Arquitetura suporta N; UI V1.x limita a 2 | V2 (3+ contas) |
| **OOS-009** | Delegação de email (secretário real que envia "em nome de") | Requer Gmail delegation API + fluxo OAuth diferente | V3 |
| **OOS-010** | Modo offline completo (zero dependência de internet) | OAuth + LLM + STT/TTS exigem cloud; offline = apenas cache + fila | V1.x já cobre o necessário |
| **OOS-011** | Classificação automática de emails por IA (prioridade, spam, newsletter) | Feature interessante mas não essencial para MVP vocal | V2 |
| **OOS-012** | Resumos de thread de email longas | Precisa LLM mais caro + UX bem pensada | V2 |
| **OOS-013** | Integração Outlook / iCloud / ProtonMail | Fora do foco Google | V2+ |
| **OOS-014** | Transcrição de reuniões (Google Meet, Zoom) | Produto completamente separado | V3 |
| **OOS-015** | Tradução automática de emails | LLM pode fazer on-demand; não é feature principal | V2 |
| **OOS-016** | Integrações Slack / Teams / Discord | Desviado do core email/calendar | V3+ |
| **OOS-017** | Modo colaborativo (2 users editam draft em tempo real) | Complexidade major + dúvida de produto | Não planeado |
| **OOS-018** | CRM / follow-up automático ("lembra-me de responder em 3 dias") | Interessante mas V2 | V2 |
| **OOS-019** | SSO empresarial (SAML, Google Workspace admin) | Foco consumer/freelancer na V1 | V3 |
| **OOS-020** | Recuperação de conta via email/SMS | Herdado da Google — se perdes a Google, perdes o Per4Biz | Nunca (by design) |

---

## 4. Como esta documentação é usada

### Em brainstorming (SPEC de feature nova)
- Antes de aceitar uma feature no escopo, verificar se está em `OOS-xxx`. Se sim → recusar ou escalar ao PO.
- Se viola um `CON-xxx` → bloqueado. Escalar imediatamente.
- Se assume algo novo → adicionar como `ASM-xxx` novo (versionar este documento).

### Em code review
- Reviewer valida: nenhuma constraint violada (especialmente CON-008/CON-009/CON-011/CON-015).
- Se código assume algo não listado em ASM → flag para discussão.

### Em PO decision
- Perguntas abertas em [05-validacao/VALIDACAO-INTERNA.md §5](../05-validacao/VALIDACAO-INTERNA.md) podem mover items de OOS para escopo V1.x — atualizar este doc quando acontece.

### Versionamento
Este documento é **living** — incrementar minor (1.1, 1.2) quando ASMs/OOS mudam; major (2.0) quando CONs mudam (raro).
