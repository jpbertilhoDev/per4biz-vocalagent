# Critérios de Aceitação — Per4Biz (Gherkin completo)

**Documento complementar do PRD.** Refere-se ao backlog em [`../04-sprints/SPRINT-PLAN.md`](../04-sprints/SPRINT-PLAN.md).

**Formato:** todos os critérios seguem `DADO QUE [contexto] / QUANDO [acção] / ENTÃO [resultado esperado]`. Cada AC tem ID rastreável (ex: `AC-E1.US1-1`). Uma user story só é **Done** quando **todos** os seus ACs passam.

**Total:** 30 user stories · ~90 ACs.

---

## Épico E1 — Autenticação & Google OAuth (13 pts)

> Nota: esta secção duplica-se parcialmente com [`../specs/e1-auth-google-oauth/SPEC.md §7`](../specs/e1-auth-google-oauth/SPEC.md). Em caso de divergência, vale o SPEC aprovado pelo PO.

### E1.US1 — Login com Google

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E1.US1-1 | o utilizador abre a PWA pela 1ª vez | clica em "Entrar com Google" | é redirecionado para o OAuth consent screen Google |
| AC-E1.US1-2 | o utilizador autoriza os 5 scopes | Google redireciona para `/auth/google/callback` | FastAPI cria linha em `auth.users` + `google_accounts` com `is_primary=true` |
| AC-E1.US1-3 | o login é bem-sucedido | tokens são guardados | o `refresh_token` fica cifrado AES-256-GCM na BD (nonce 12B + ciphertext + tag) |
| AC-E1.US1-4 | o utilizador cancela no consent screen | Google redireciona com `?error=access_denied` | app mostra toast "Login cancelado — aceita para usar o Per4Biz" |

### E1.US2 — Sessão persistente

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E1.US2-1 | fiz login há < 7 dias | fecho e reabro o PWA | sou redirecionado diretamente para `/inbox` sem login |
| AC-E1.US2-2 | o JWT Supabase expirou | abro o PWA | `@supabase/ssr` refresca silenciosamente e mostra `/inbox` |
| AC-E1.US2-3 | instalei o PWA como standalone no iOS | força-fecho a app | a sessão persiste via cookie HTTP-only `__Host-` |

### E1.US3 — Revogar acesso

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E1.US3-1 | tenho sessão ativa | vou a Definições → Conta Google → "Desvincular e apagar" | abre modal pedindo confirmação com texto "APAGAR" |
| AC-E1.US3-2 | confirmo a revogação | app processa | `POST https://oauth2.googleapis.com/revoke` é chamado + cascata de DELETE em `google_accounts`, `email_cache`, `draft_responses`, `voice_sessions` |
| AC-E1.US3-3 | a revogação completa | app reage | redirect para `/` com toast "Conta apagada com sucesso" |

### E1.US4 — Refresh automático de tokens

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E1.US4-1 | o `access_token` Google expirou (> 1h) | FastAPI precisa chamar Gmail API | obtém novo `access_token` via `refresh_token` transparentemente |
| AC-E1.US4-2 | o `refresh_token` é inválido (`invalid_grant`) | próxima chamada Google | FastAPI detecta, apaga `google_accounts`, força re-login com toast "Acesso revogado no Google" |
| AC-E1.US4-3 | o refresh acontece | novo access_token é emitido | é re-cifrado AES-256-GCM antes de escrever na BD |

---

## Épico E2 — Microserviço Python Gmail (21 pts)

### E2.US1 — `/emails/list` paginado

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E2.US1-1 | tenho 1 conta conectada com emails | chamo `GET /emails?account_id=X&limit=20` | recebo JSON com 20 items: `{id, from, subject, snippet, received_at, is_read}` |
| AC-E2.US1-2 | passo `cursor` da página anterior | API processa | retorna os 20 seguintes em ordem `received_at DESC` |
| AC-E2.US1-3 | a conta não me pertence (`user_id` diferente) | chamo o endpoint | recebo `403 Forbidden` — RLS bloqueia cross-tenant |

### E2.US2 — `/emails/{id}` parseado

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E2.US2-1 | existe email com `gmail_message_id=X` na minha conta | chamo `GET /emails/X` | recebo `{headers, body_text, body_html_cleaned, attachments_meta}` |
| AC-E2.US2-2 | o email é HTML complexo | API processa | HTML é sanitizado (BeautifulSoup + bleach); texto limpo é devolvido para TTS |
| AC-E2.US2-3 | o email é consultado | acesso é registado | `email_cache.body_cached` é preenchido com TTL `now() + 24h` |

### E2.US3 — `/emails/send` autenticado

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E2.US3-1 | tenho draft aprovado pelo user | `POST /emails/send` com `{account_id, draft_id}` | Gmail API envia e devolve `gmail_message_id` |
| AC-E2.US3-2 | `draft_responses.status` não é `approved` | chamo `/emails/send` | `400 Bad Request` — "Draft não aprovado" |
| AC-E2.US3-3 | envio sucede | app atualiza BD | `draft_responses.status = 'sent'` + `sent_at = now()` |

### E2.US4 — Rate limiting + circuit breaker

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E2.US4-1 | user faz > 60 req/min | Upstash Redis conta | próxima request → `429 Too Many Requests` com header `Retry-After` |
| AC-E2.US4-2 | Gmail API devolve 5xx 3× seguidas | circuit breaker (`arq` middleware) dispara | próximas chamadas rejeitam imediatamente por 60s + cache local é servido |
| AC-E2.US4-3 | o circuito recupera | health-check passa | breaker reabre automaticamente |

### E2.US5 — Logs estruturados

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E2.US5-1 | qualquer request entra no FastAPI | middleware loga | Axiom recebe `{request_id, user_id, path, status, latency_ms}` — sem PII |
| AC-E2.US5-2 | ocorre exception | handler captura | Sentry recebe event com `user_id` (não email) e stacktrace redacted |

---

## Épico E3 — Inbox PWA (18 pts)

### E3.US1 — Lista de 50 emails

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E3.US1-1 | tenho emails na conta ativa | abro o tab Inbox | vejo lista com remetente, assunto, snippet ≤ 100 chars, hora formatada em PT-PT |
| AC-E3.US1-2 | existem não lidos | lista renderiza | items não lidos têm assunto em `font-weight: 600` + dot colorido da conta |
| AC-E3.US1-3 | inbox vazia | lista renderiza | vejo ilustração + texto "Inbox limpa. Bom trabalho!" |

### E3.US2 — Pull-to-refresh

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E3.US2-1 | estou no topo da lista | puxo para baixo > 80px | waveform animado aparece (3 ondas) em vez de spinner |
| AC-E3.US2-2 | solto o gesto | sync dispara | haptic `selection` + fetch incremental de novos emails |

### E3.US3 — Abrir email em tela cheia

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E3.US3-1 | tap num item da inbox | transição iOS-like (280ms cubic-bezier) | abre tela de detalhe com header (remetente, destinatários, data, conta) + corpo legível |
| AC-E3.US3-2 | email é aberto | frontend chama `PATCH /emails/{id}` | `is_read=true` + badge da inbox decrementa |

### E3.US4 — PWA instalável

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E3.US4-1 | 3ª sessão do user | app detecta | mostra banner "Instala para acesso rápido" (dismissível) |
| AC-E3.US4-2 | user instala no iOS | Safari adiciona | app abre em modo standalone (sem chrome), splash `#0A84FF`, ícone maskable |
| AC-E3.US4-3 | user instala no Android | Chrome adiciona | `display: standalone` + theme_color correto + shortcuts funcionam |

### E3.US5 — Badge de não lidos

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E3.US5-1 | tenho N emails não lidos | abro app | top bar mostra `N` em badge |
| AC-E3.US5-2 | N > 99 | renderiza | mostra `99+` |

---

## Épico E4 — Voice Agent (26 pts)

### E4.US1 — TTS play button

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E4.US1-1 | abro email | botão "🔊 Ouvir" aparece no header | tap → ElevenLabs streaming começa em < 1s |
| AC-E4.US1-2 | TTS está a tocar | tap de novo | pausa; novo tap retoma do mesmo ponto |
| AC-E4.US1-3 | email tem HTML | TTS processa | lê apenas texto limpo (sem "background-color: red" etc) |

### E4.US2 — Gravar com indicador visual

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E4.US2-1 | tap no VoiceButton idle (azul) | começa gravação | cor muda para vermelho `#FF375F`, pulsa 1.5s, waveform reativo ao volume |
| AC-E4.US2-2 | user solta (PTT) OU dá segundo tap | gravação termina | blob webm/opus é enviado para `POST /voice/process` |
| AC-E4.US2-3 | user nega permissão de mic | iOS/Android bloqueia | modal: "Para usar voz, permite microfone nas definições do browser" + fallback para input texto |

### E4.US3 — Transcrição em tempo real

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E4.US3-1 | estou a gravar | Groq Whisper streaming (ou WebSocket) | transcrição aparece no centro da tela em 22px/500 |
| AC-E4.US3-2 | palavras ainda não confirmadas | renderização | mostram-se em cinza 60% opacity |
| AC-E4.US3-3 | palavra é confirmada | renderização | fade de cinza para preto em 120ms |

### E4.US4 — LLM polisse ditado

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E4.US4-1 | ditei resposta bruta | Claude 3.5 Sonnet processa | recebo draft em PT-PT formal (não PT-BR) em < 2.5s |
| AC-E4.US4-2 | é reply a email | prompt inclui contexto da thread | resposta faz sentido no fio |
| AC-E4.US4-3 | LLM timeout > 15s | middleware cancela | toast "Demorou muito — tenta escrever manualmente" + fallback textarea |

### E4.US5 — Métricas de latência

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E4.US5-1 | voice session completa | pipeline termina | Axiom recebe `{session_id, stt_ms, intent_ms, llm_ms, tts_ms, total_ms}` |
| AC-E4.US5-2 | p95 total > 4s em 1h | alerta dispara | Axiom webhook → Slack/email ao JP |

---

## Épico E5 — Composer Vocal & Envio (16 pts)

### E5.US1 — Revisar draft

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E5.US1-1 | LLM gerou draft | UI mostra | card com assunto + corpo completo + 3 CTAs (Enviar / Editar / Descartar) |
| AC-E5.US1-2 | leio o draft | sem ação | o draft só é enviado após CTA "Enviar" explícito |

### E5.US2 — Editar por texto

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E5.US2-1 | tap no corpo do draft | teclado abre | edição inline preserva formatação básica |
| AC-E5.US2-2 | edito texto | backend regista | `draft_responses.body_text` atualiza; `llm_model` marcado como `human_edited` |

### E5.US3 — Re-ditar sem perder

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E5.US3-1 | tenho draft visível | tap em "Refazer" | modal: "Manter original? [Sim, duplicar / Não, substituir]" |
| AC-E5.US3-2 | escolho duplicar | histórico preserva | `draft_responses` nova row com `parent_draft_id` referenciando a anterior |

### E5.US4 — Confirmar envio 1-tap

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E5.US4-1 | tap em "Enviar" | haptic success | `POST /emails/send` + botão vira barra de progresso horizontal |
| AC-E5.US4-2 | Gmail retorna 200 | draft status | `status='sent'`, `sent_at=now()`, `gmail_message_id` guardado |

### E5.US5 — Confirmação "Enviado"

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E5.US5-1 | envio sucede | UI reage | checkmark verde 400ms + haptic success + bip de confirmação (se som ON) |
| AC-E5.US5-2 | 800ms depois | auto-dismiss | modal composer fecha; volto à lista com toast "Email enviado" |

---

## Épico E6 — Multi-conta (16 pts, V1.x)

### E6.US1 — Adicionar 2ª conta

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E6.US1-1 | tenho 1 conta | vou a Definições → Contas → "+ Adicionar" | inicia OAuth flow com `prompt=select_account` |
| AC-E6.US1-2 | tento adicionar a mesma conta | callback detecta duplicate | erro "Esta conta já está ligada" sem duplicar row |
| AC-E6.US1-3 | sucede | BD atualiza | nova row em `google_accounts` com `color_hex` auto-atribuída da paleta de 6 |

### E6.US2 — Seletor de conta

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E6.US2-1 | tenho ≥ 2 contas | swipe down 40px no header | overlay com chips grandes aparece (tap filtra inbox) |
| AC-E6.US2-2 | seleciono 2ª conta | state atualiza | inbox recarrega em < 500ms; `users.active_account_id` persiste |

### E6.US3 — Inbox unificada

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E6.US3-1 | toggle "Unificada" ON | query backend | `SELECT FROM email_cache WHERE account_id IN (...) ORDER BY received_at DESC` |
| AC-E6.US3-2 | cada item renderiza | UI lateral | barra colorida 4px esquerda = cor da conta de origem |

### E6.US4 — Escolher conta no envio

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E6.US4-1 | abro composer vocal | sistema sugere | default = conta que recebeu o email (se reply) OU `active_account_id` |
| AC-E6.US4-2 | tap no chip "De: …" | dropdown | lista todas as contas; tap troca |

---

## Épico E7 — Calendar & Contacts (21 pts, V2)

### E7.US1 — Criar evento por voz

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E7.US1-1 | digo "marca reunião amanhã às 15h com Ana" | LLM extrai entities | `{start: tomorrow 15:00 Europe/Lisbon, attendees: [Ana via Contacts], title: "Reunião"}` |
| AC-E7.US1-2 | confirmação obrigatória | UI mostra | card "Criar evento às 15h de amanhã com Ana Costa?" → Sim / Não |
| AC-E7.US1-3 | confirmo | Google Calendar API | evento criado + aparece na agenda imediatamente |

### E7.US2 — Agenda do dia na home

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E7.US2-1 | tenho eventos hoje | abro Agenda | timeline vertical mostra todos com cor por conta |
| AC-E7.US2-2 | sem eventos | renderiza | "Nada marcado para hoje — bom dia livre." |

### E7.US3 — Resolver contato por voz

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E7.US3-1 | digo "responder ao João" | People API search | match único → usa email automaticamente |
| AC-E7.US3-2 | ambíguo (2 Joãos) | UI pergunta | "Qual João? João Silva ou João Costa?" |
| AC-E7.US3-3 | sem match | fallback | "Não encontrei ninguém com esse nome nos teus contactos" |

### E7.US4 — Confirmação visual de evento

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E7.US4-1 | LLM extraiu dados do evento | pré-criação | card visual com título, data, hora, convidados editáveis |
| AC-E7.US4-2 | edito manualmente | override | valores ditados são sobrescritos pelos editados |

---

## Épico E8 — Notifications & Offline (13 pts, V2)

### E8.US1 — Push notification

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E8.US1-1 | novo email importante chega | Gmail Pub/Sub → FastAPI | `web-push` envia notification ao endpoint subscrito |
| AC-E8.US1-2 | iOS PWA instalado (16.4+) | notification chega | título "Novo email de X" sem corpo (privacidade) |
| AC-E8.US1-3 | user tap na notification | deep link | abre app direto no email específico |

### E8.US2 — Fila offline

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E8.US2-1 | estou offline | tento enviar draft | guarda em IndexedDB `outbox` + toast "Será enviado quando voltares online" |
| AC-E8.US2-2 | reconnecto | Service Worker Background Sync | processa outbox; envia cada draft; atualiza status |

### E8.US3 — Status online/offline

| ID | Dado que… | Quando… | Então… |
|---|---|---|---|
| AC-E8.US3-1 | perco ligação | `navigator.onLine = false` | banner sutil "Offline — a ver emails guardados" no top |
| AC-E8.US3-2 | reconnecto | evento `online` | banner desaparece com fade + sync automático |

---

## Resumo — Cobertura de ACs

| Épico | User Stories | ACs totais | Pts |
|---|---|---|---|
| E1 | 4 | 13 | 13 |
| E2 | 5 | 13 | 21 |
| E3 | 5 | 11 | 18 |
| E4 | 5 | 13 | 26 |
| E5 | 5 | 10 | 16 |
| E6 | 4 | 9 | 16 |
| E7 | 4 | 10 | 21 |
| E8 | 3 | 7 | 13 |
| **Total** | **35** | **86** | **144** |

*Pequenas variações vs SPRINT-PLAN (147 pts) devidas a arredondamentos em refinamento — validar em planning.*

---

## Como usar este documento

1. **Antes de fechar uma user story como Done:** percorrer todos os ACs dela. Se algum falha → não está Done.
2. **No SPEC de cada feature** (`../specs/<feature>/SPEC.md`): copiar os ACs relevantes, refinar com edge cases específicos do contexto.
3. **Em PLAN.md** (`../plans/<feature>/PLAN.md`): cada AC mapeia ≥ 1 teste (unit, integration ou E2E) — ver [TESTING-STRATEGY.md](TESTING-STRATEGY.md).
4. **Numa PR:** descrição deve listar ACs cobertos (`Closes AC-E2.US1-1, AC-E2.US1-2`) — facilita code review.
