# Per4Biz V1 Completo — Design Spec

**Data:** 2026-04-16
**Autor:** JP Bertilho (PO) + Claude (arquiteto)
**Status:** Aprovado em brainstorming oral · aguarda revisão escrita
**Substitui:** decisões de escopo V1/V2 em `01-prd/PRD-MASTER.md §6` e `07-v1-scope/EXECUTION-NOTES.md §6`
**Precede:** plano de implementação em `plans/per4biz-v1-completo/PLAN.md` (a ser gerado via skill `writing-plans`)

---

## 1. Contexto e motivação

O Per4Biz foi inicialmente partido em fases (V1 = email+voz em 13 semanas; V2 = calendar+contacts pós-beta; V1.x = multi-conta). O documento `07-v1-scope/EXECUTION-NOTES.md` cortou ainda mais para self-use (remove RLS, Auth Supabase, CASA, rate limiting, etc.).

Em 2026-04-16 o PO decidiu **promover Calendar e Contacts para V1**, mantendo **multi-conta fora** (continua V2). A motivação é que a visão original do produto — "copiloto/secretário vocal completo" — só faz sentido quando o Vox consegue ler email, gerir agenda e resolver contactos de forma integrada. Entregar V1 sem calendar/contacts seria entregar metade do valor.

Este spec consolida o novo escopo e serve de fonte-de-verdade para os sprints 4 a 9.

---

## 2. Visão consolidada

Per4Biz é um **PWA mobile (iOS/Android)** instalável que actua como **secretário vocal pessoal** do JP, numa **única conta Google**, cobrindo Gmail + Calendar + Contacts. O agente **Vox** é a tela principal (chat-first). Tudo se faz a falar; o teclado é fallback.

**Posicionamento:** "Superhuman encontra Siri para profissionais que vivem no Google Workspace." O diferencial é o paradigma conversacional multi-serviço em PT-PT.

**Target de self-use V1:** JP usa o Per4Biz como ferramenta diária de produtividade por ≥ 14 dias consecutivos sem voltar a abrir as apps nativas do Google.

---

## 3. Escopo V1 (revisto)

### 3.1 Matriz do que entra / fica fora

| Área | V1 (agora) | Fora (V2 ou futuro) |
|---|---|---|
| **Auth Google** | 1 conta, OAuth 2.0, tokens AES-256-GCM | Multi-conta, Supabase Auth, RLS, CASA, signup multi-user |
| **Email** | Ler, listar, responder, enviar, outbox offline | Threading avançado, labels custom, anexos pesados |
| **Voz** | Groq Whisper v3 STT + Llama 3.3 70B intents/drafts + ElevenLabs PT-PT feminina + auto-silêncio 2s + memória multi-turn | Wake-word, streaming TTS full-duplex |
| **Calendar** | **CRUD completo por voz** (list/create/edit/delete) + `dateparser` PT + card de confirmação | Recurring events complexos, convites a terceiros, multi-calendar |
| **Contacts** | **Pesquisa + create + edit por voz** + resolução automática de destinatários | Lembretes relacionais tipo CRM, grupos custom |
| **Real-time** | **Gmail Push (Pub/Sub) + Supabase Realtime → PWA + Web Push (VAPID)** filtrado por "contactos conhecidos" | Triagem IA de importância, VIP lists manuais, regras complexas |
| **Bridge email↔calendar** | Vox lê email → LLM detecta menção de reunião → oferece card "marcar na agenda?" | Detecção 100% automática sem prompt do utilizador |
| **UI** | Chat-first dark `#0A0A0F` violet+cyan, bottom navbar 4 tabs (Chat · Inbox · Agenda · Settings), Vox cards (8 tipos), MicButton 5 estados | Tema claro, desktop nativo, i18n PT-BR/EN |

### 3.2 Alterações vs docs existentes

- `01-prd/PRD-MASTER.md §6`: **RF-9 (Calendar) e RF-10 (Contacts) sobem de V2 para V1**. RF-2 (multi-conta) **continua V2**.
- `04-sprints/SPRINT-PLAN.md`: Sprints 4-6 substituídos por Sprints 4-9 (6 sprints de 2 semanas).
- `07-v1-scope/EXECUTION-NOTES.md §6`: remover `[ ] Calendar integration (V2)` e `[ ] Contacts integration (V2)`. Manter fora: RLS, Supabase Auth, CASA, multi-user, mTLS, rate limiting Upstash.
- `02-ultraplan/ULTRAPLAN-tecnico.md`: adicionar secções 4.x Calendar API, 4.y Contacts API, 9.x Gmail Push architecture, 9.y Web Push + VAPID. **Remover Claude** do §2.6 (fica Groq-only).

### 3.3 Timeline

- **6 sprints × 2 semanas = 12 semanas** a partir de 2026-04-21
- V1.0-demo (bridge funcional): fim do Sprint 8 (~10 semanas)
- V1 production-ready self-use: fim do Sprint 9 (~12 semanas)

---

## 4. Épicos & User Stories

### 4.1 Mapa de épicos

| # | Épico | Pts | Sprint | Status |
|---|---|---|---|---|
| E1 | Auth & Google OAuth | 13 | — | ✅ Done |
| E2 | Gmail backend | 21 | — | ✅ Done |
| E3 | Inbox PWA | 18 | — | ✅ Done |
| E4 | Voice Agent | 26 | — | ✅ Done |
| E5 | Composer Vocal & Envio | 16 | — | ✅ Done |
| **E9** | **Chat-First Redesign + Memória Vox** | 28 | S4 | ⬜ |
| **E7** | **Calendar Vertical (CRUD por voz)** | 25 | S5 | ⬜ |
| **E8** | **Contacts Vertical (pesquisa + CRUD)** | 18 | S6 | ⬜ |
| **E11** | **Real-time (Gmail Push + Web Push)** | 26 | S7 | ⬜ |
| **E12** | **Bridge IA Email↔Calendar** | 16 | S8 | ⬜ |
| **E10** | **Polish & Self-use Production** | 18 | S9 | ⬜ |

**Total Done:** 94 pts · **Total Novo V1:** 131 pts · **Velocity esperada:** ~22 pts/sprint

### 4.2 E9 — Chat-First Redesign + Memória Vox (28 pts)

Absorve o WIP de memória de conversação + o redesign chat-first já planeado.

- **E9.US1 (5)** Bottom navbar 4 tabs (Chat · Inbox · Agenda · Settings) com paleta dark violet+cyan
- **E9.US2 (8)** Vox cards base (8 tipos: `email-read`, `transcription`, `draft`, `confirmation`, `error`, `agenda-event`, `contact-result`, `bridge-suggest`)
- **E9.US3 (5)** MicButton 5 estados (idle/listening/silence-detected/processing/error) + auto-silêncio 2s + transcrição em tempo real (confirmed/hypothesis)
- **E9.US4 (5)** **Memória multi-turn**: `chat-store` com `persist` (localStorage, cap 50 msgs), `history[]` enviado ao `/voice/intent`, contexto temporal ISO injectado no system prompt
- **E9.US5 (3)** Inbox redesenhada como tab secundária (preserva componentes E3, sem regressão)
- **E9.US6 (2)** Onboarding básico: splash + login Google + Vox apresenta-se no chat

### 4.3 E7 — Calendar Vertical (25 pts)

- **E7.US1 (5)** Backend `/calendar/events` GET/POST/PATCH/DELETE via Google Calendar API (Python `google-api-python-client`)
- **E7.US2 (5)** `dateparser` PT integrado — normaliza "próxima quinta 15h" → ISO 8601 `Europe/Lisbon` **antes** do LLM
- **E7.US3 (5)** Intents Vox completos: `calendar_list`, `calendar_create`, `calendar_edit`, `calendar_delete`
- **E7.US4 (5)** Card `agenda-event` com interpretação visível (summary, data/hora, local) + CTA Confirmar/Cancelar antes de commit
- **E7.US5 (3)** OAuth scope `https://www.googleapis.com/auth/calendar.events` adicionado + fluxo de re-consent para tokens existentes
- **E7.US6 (2)** Tab Agenda mostra próximos 7 dias (lista read-only; criação só por voz)

### 4.4 E8 — Contacts Vertical (18 pts)

- **E8.US1 (3)** Backend `/contacts` GET (search) / POST (create) / PATCH (edit) via Google People API
- **E8.US2 (3)** Intents: `contacts_search`, `contacts_create`, `contacts_edit`
- **E8.US3 (5)** Resolução automática de destinatário: "responde ao João" → Vox pesquisa, se 1 match usa, se N pergunta "o João Costa ou o João Silva?"
- **E8.US4 (3)** Card `contact-result` com dados (nome, email, telefone) lidos em voz
- **E8.US5 (2)** OAuth scope `https://www.googleapis.com/auth/contacts`
- **E8.US6 (2)** Settings mostra sync status Contacts + total de contactos em cache

### 4.5 E11 — Real-time Gmail Push + Web Push (26 pts)

- **E11.US1 (8)** Setup Google Cloud Pub/Sub (projecto, tópico `gmail-watch`, service account) + chamada `gmail.users.watch()` + cron de renovação semanal (Fly.io scheduled machine)
- **E11.US2 (5)** Webhook FastAPI `POST /webhooks/gmail` valida JWT assinado do Pub/Sub, chama `history.list` para deltas, publica em Realtime
- **E11.US3 (3)** Supabase Realtime channel `inbox:{user_id}` — backend publica mudanças, frontend subscreve, inbox actualiza sem refresh
- **E11.US4 (5)** Web Push API + VAPID keypair + service worker recebe notificações + action "Ouvir com Vox" abre chat
- **E11.US5 (3)** Filtro "remetente conhecido" — verifica `from` contra `contacts_cache` antes de enviar push; se não existe, só actualiza inbox (sem notificação)
- **E11.US6 (2)** Settings: toggle "push notifications" on/off + botão "renovar permissão"

### 4.6 E12 — Bridge IA Email↔Calendar (16 pts)

- **E12.US1 (5)** Detector LLM: quando Vox lê email, segunda passagem Llama extrai `[{summary, start_iso, end_iso, location, confidence}]`
- **E12.US2 (5)** Card `bridge-suggest` aparece após leitura se detecção com confidence ≥ 0.7: "Detectei reunião quinta 15h. Marcar na agenda?"
- **E12.US3 (3)** Aceitar card → reutiliza fluxo `calendar_create` com pré-preenchimento + card de confirmação (sem bypass)
- **E12.US4 (3)** Múltiplas datas → Vox pergunta "Qual destas queres marcar?" com card multi-opção

### 4.7 E10 — Polish & Self-use Production (18 pts)

- **E10.US1 (3)** Onboarding polido: splash + 2 ecrãs + login guiado pelo Vox no chat
- **E10.US2 (3)** p95 latência STT+LLM+TTS < 4s (benchmark com 50 interacções reais + optimizações)
- **E10.US3 (3)** Outbox offline: fila local de envios + retry exponencial quando volta a rede
- **E10.US4 (2)** Indicador online/offline no header
- **E10.US5 (2)** Crash-free sessions ≥ 99% (Sentry lite ou Axiom custom)
- **E10.US6 (2)** Métricas self-use em dashboard simples: sessões/dia, emails respondidos/dia, tempo médio
- **E10.US7 (3)** Tuning do tom PT-PT do Vox: system prompt refinado com 20 casos reais de teste

---

## 5. Sprint Plan (6 sprints)

| Sprint | Épico | Semanas | Goal | Demo |
|---|---|---|---|---|
| **S4** | E9 | 1-2 | Chat-first funciona e o Vox lembra-se da conversa | Chat completo + memória persistente + MicButton auto-silêncio |
| **S5** | E7 | 3-4 | Marco e gere agenda só a falar | "Marca reunião Maria quinta 15h" → evento real no Google Calendar |
| **S6** | E8 | 5-6 | Respondo a qualquer pessoa do catálogo por voz | "Qual o email do João?" + "responde ao João" com resolução automática |
| **S7** | E11 | 7-8 | Recebo emails em tempo real com push inteligente | Email novo de contacto conhecido → notificação em <5s no telemóvel |
| **S8** | E12 | 9-10 | Vox detecta compromissos nos emails e propõe agendar | Ler email com "quinta 15h" → card "marcar?" → confirmar → evento criado |
| **S9** | E10 | 11-12 | JP usa Per4Biz diariamente sem fricção | Métricas self-use após 1 semana de uso real, p95 < 4s, crash-free ≥ 99% |

### 5.1 Definition of Done (por sprint)

1. Todas as ACs do épico verdes (ver §7)
2. Testes: unit ≥ 80% cobertura nova · integration nos endpoints novos · E2E happy path da story principal
3. Typecheck + lint verdes (frontend `tsc --noEmit` + ESLint; backend `ruff` + `mypy`)
4. Demo gravada (JP a usar ao vivo) revista antes de fechar
5. PR merged em `main` com Conventional Commits + AC references (`Closes AC-E7.1`)

---

## 6. Arquitectura (deltas vs ULTRAPLAN actual)

### 6.1 Diagrama

```
        iOS / Android (PWA instalável)
                │
    ┌───────────┴────────────┐
    │  Next.js 16 PWA        │  ← chat-first dark
    │  - chat-store (persist)│
    │  - service worker      │  ← Web Push receiver
    │  - Supabase Realtime   │  ← subscribe inbox:{user_id}
    └───────────┬────────────┘
                │ HTTPS bearer
                ▼
    ┌────────────────────────┐       ┌─────────────────────┐
    │  FastAPI Python 3.12   │◄─────►│ Google Pub/Sub      │
    │  (Fly.io mad)          │ push  │ tópico gmail-watch  │
    │                        │       └─────────────────────┘
    │  /auth/google/*        │
    │  /emails/*             │
    │  /calendar/events/*    │──┐
    │  /contacts/*           │  │    ┌─────────────────────┐
    │  /voice/intent         │  ├───►│ Google APIs         │
    │  /voice/stt /tts       │  │    │ Gmail · Cal · People│
    │  /voice/bridge/detect  │  │    └─────────────────────┘
    │  /webhooks/gmail       │◄─┘
    │  /notifications/*      │
    │  /cron/renew-watches   │
    └──────────┬─────────────┘
               │
    ┌──────────┴──────────────┐
    │  Supabase (EU)          │
    │  - postgres (schema §6.3)│
    │  - Realtime channels    │  ← novo
    │  - Storage              │
    └─────────────────────────┘

    External:
    - Groq (Whisper v3 + Llama 3.3 70B) — STT + intents + drafts + bridge detector
    - ElevenLabs (TTS PT-PT fem. streaming)
```

### 6.2 Endpoints novos (FastAPI)

| Endpoint | Método | Scope OAuth | Notas |
|---|---|---|---|
| `/calendar/events` | GET | `calendar.readonly` | query `days`, `from`, `to` |
| `/calendar/events` | POST | `calendar.events` | body: summary, start, end (ISO), location? |
| `/calendar/events/{id}` | PATCH | `calendar.events` | partial update |
| `/calendar/events/{id}` | DELETE | `calendar.events` | soft confirm no client obrigatório |
| `/contacts` | GET | `contacts.readonly` | query `q`, `limit` |
| `/contacts` | POST | `contacts` | body: name, emails[], phones[] |
| `/contacts/{id}` | PATCH | `contacts` | partial |
| `/voice/intent` | POST | — | **expandido**: body aceita `history[]`, intents novos |
| `/voice/bridge/detect` | POST | — | **novo**: recebe corpo email, devolve candidatos de evento |
| `/webhooks/gmail` | POST | — | valida JWT Pub/Sub, chama `history.list`, publica Realtime |
| `/notifications/subscribe` | POST | — | regista subscription VAPID |
| `/notifications/send` | POST (interno) | — | Web Push filtrando por contactos conhecidos |
| `/cron/renew-watches` | GET (Fly.io cron) | — | renova `users.watch()` antes dos 7 dias |

### 6.3 Novas tabelas (Postgres)

```sql
-- Calendar events cache (opcional, UI rápida; fonte = Google)
create table calendar_events_cache (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  google_event_id text not null,
  google_calendar_id text not null default 'primary',
  summary text,
  start_at timestamptz not null,
  end_at timestamptz not null,
  location text,
  raw jsonb,
  updated_at timestamptz default now(),
  unique(user_id, google_event_id)
);
create index on calendar_events_cache (user_id, start_at);

-- Contacts cache
create table contacts_cache (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  google_resource_name text not null,  -- "people/c12345"
  display_name text,
  emails text[] default '{}',
  phones text[] default '{}',
  raw jsonb,
  updated_at timestamptz default now(),
  unique(user_id, google_resource_name)
);
create index on contacts_cache using gin (emails);
create index on contacts_cache using gin (to_tsvector('simple', display_name));

-- Gmail watch state
create table gmail_watches (
  user_id uuid primary key,
  google_account_id uuid not null,
  history_id text not null,
  expiration timestamptz not null,
  topic_name text not null,
  renewed_at timestamptz default now()
);

-- Web Push subscriptions
create table push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  created_at timestamptz default now()
);

-- Bridge detections (audit)
create table bridge_detections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  email_id text not null,
  detected_at timestamptz default now(),
  candidates jsonb,  -- [{summary, start_iso, end_iso, location, confidence}]
  accepted_event_id uuid references calendar_events_cache(id),
  dismissed boolean default false
);
```

**Nota:** sem policies RLS (mantém `07-v1-scope §6`). `user_id` hardcoded no backend para UUID fixo do JP. Todas as tabelas preparadas para multi-tenant via migração trivial futura.

### 6.4 Fonte-de-verdade: Google, sempre

Google (Gmail, Calendar, People) é **sempre a fonte-de-verdade**. A base de dados Supabase é **só cache** para UI rápida + degradação graciosa offline.

- Writes: Vox → backend → Google API → cache
- Se Google API falha: **não grava em cache**, mostra erro claro ao utilizador
- Reads: backend consulta cache se fresco, senão Google + actualiza cache
- Sync: `history_id` (Gmail), ETag (Calendar), `sync_token` (People)

### 6.5 Scopes OAuth (actualizados)

```
# Existente (manter)
openid
email
profile
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send

# Novo V1 (pedir re-consent)
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/contacts
```

Re-consent é necessário; o onboarding do Sprint 5 explica e guia.

### 6.6 Dependências novas

**Python:**
- `dateparser` — parsing datas PT
- `google-cloud-pubsub` — validação Pub/Sub subscriber
- `pywebpush` — enviar notificações VAPID

**Node (frontend):**
- `zustand/middleware` — já em WIP (persist)
- Web Push API é nativa do browser + service worker (sem npm dep)

**Infra:**
- Google Cloud: activar Pub/Sub API + tópico `gmail-watch` + service account
- VAPID keypair (guardada em Fly.io secrets)
- Fly.io scheduled machine para cron `/cron/renew-watches`

### 6.7 ADRs novos

- **ADR-008** — **Cache vs fonte-de-verdade.** Google é sempre a fonte. Cache local serve só UX rápida + offline. Sync via `history_id` (Gmail), ETag (Calendar), `sync_token` (People).
- **ADR-009** — **Bridge detector separado.** 2ª chamada LLM separada da classificação de intent (`/voice/bridge/detect`). Permite ajustar temperatura/prompt sem afectar outro tráfego. Rate-limited a 1× por email aberto.
- **ADR-010** — **Validação Pub/Sub.** JWT no header `Authorization: Bearer <token>` assinado pelo Google, verificar `aud` = webhook URL e `email` = service account autorizado. Rejeitar tudo o resto com 401.

---

## 7. Acceptance Criteria críticos

### E9 — Chat-first + Memória Vox

- **AC-E9.1** Após refresh da página, mensagens do chat persistem (últimas 50)
- **AC-E9.2** `POST /voice/intent` com `history[]` de 5 turnos resolve referências ("essa reunião", "ele", "amanhã") com accuracy ≥ 90% em 20 casos de teste
- **AC-E9.3** MicButton pára automaticamente após 2s de silêncio (configurável 1-5s em Settings)
- **AC-E9.4** Inbox existente acessível em `/inbox` sem regressão dos testes E1-E5

### E7 — Calendar

- **AC-E7.1** "marca reunião com a Maria quinta às 15h" cria evento real no Google Calendar (verificável em `calendar.google.com`)
- **AC-E7.2** `dateparser` resolve ≥ 95% de 30 frases PT ("amanhã", "próxima segunda", "daqui a 2 semanas", "sexta que vem")
- **AC-E7.3** Antes de commit, card mostra interpretação exacta; cancelar no card = zero escrita em Google
- **AC-E7.4** "passa a reunião para sexta" sobre contexto anterior edita o evento correcto
- **AC-E7.5** Falha do Google API retorna erro visível ao utilizador; cache não regista sucesso falso

### E8 — Contacts

- **AC-E8.1** "qual é o email da Maria Silva?" devolve email em voz em <3s
- **AC-E8.2** "responde ao João" com 3 Joãos abre card de desambiguação; com 1 resolve sem perguntar
- **AC-E8.3** "adiciona João Costa, joao@x.pt" cria contacto real no Google Contacts
- **AC-E8.4** Pesquisa funciona offline com cache local (degradação graciosa)

### E11 — Real-time

- **AC-E11.1** Novo email entra na inbox da PWA em <5s sem refresh (app aberta)
- **AC-E11.2** Email de remetente em `contacts_cache` dispara push; desconhecido não dispara
- **AC-E11.3** Tocar na notificação abre chat com email aberto para Vox ler
- **AC-E11.4** `users.watch()` renova automaticamente antes de 7 dias (cron Fly.io)
- **AC-E11.5** Webhook Pub/Sub valida JWT — requests sem token assinado retornam 401

### E12 — Bridge IA

- **AC-E12.1** Email com "reunião quinta às 15h no Starbucks Saldanha" gera card `bridge-suggest` com datetime+local parseados
- **AC-E12.2** Detector não oferece card em emails sem referências temporais (false positive rate <10% em 30 emails)
- **AC-E12.3** Aceitar card reutiliza `calendar_create` com mesma confirmação de E7 (sem bypass)
- **AC-E12.4** Múltiplas datas detectadas → Vox pergunta qual

### E10 — Polish

- **AC-E10.1** p95 latência STT+LLM+TTS medida em 50 interacções reais < 4000ms
- **AC-E10.2** Envio offline enfila; ao voltar rede dispara com retry exponencial
- **AC-E10.3** Crash-free sessions ≥ 99% numa semana de uso real
- **AC-E10.4** Métricas self-use visíveis em dashboard simples

---

## 8. Riscos

| # | Risco | Prob | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | Gmail Push (Pub/Sub) setup complexo | Alta | Alto | S7 dedicado com 2 semanas; fallback = polling 30s se Pub/Sub falhar |
| R2 | LLM interpreta data/hora errada | Média | Alto | `dateparser` PT **antes** do LLM + card de confirmação obrigatório + testes com 30 casos |
| R3 | Web Push no iOS só 16.4+ | Média | Médio | Requisito mínimo iOS 16.4 documentado; fallback = sem push, app aberta recebe via Realtime |
| R4 | Bridge detector gera false positives | Média | Médio | Card é sempre opcional, nunca auto-cria; utilizador dismissa. Tuning via `bridge_detections` |
| R5 | Custo Groq explode com 2ª chamada LLM do bridge | Baixa | Médio | Rate-limit 1× por email aberto; monitor custo semanal |
| R6 | Re-consent Google quebra tokens existentes | Alta | Alto | Onboarding em S5 explica re-consent; fallback graceful se scope falha |
| R7 | Auto-silêncio corta utilizador com pausas | Média | Médio | Configurável 1-5s em Settings; default 2s |
| R8 | Refactor chat-first quebra E1-E5 | Média | Alto | Preserva componentes existentes; E2E regression obrigatória no S4 |

---

## 9. Métricas de sucesso V1 (self-use)

**Produto:**
- Emails respondidos por voz/dia: ≥ 5 (semana normal)
- Eventos criados por voz/semana: ≥ 3
- Contactos pesquisados por voz/semana: ≥ 5
- Bridge suggestions accept rate: ≥ 40%

**Técnicas:**
- p95 latência voz end-to-end: < 4s
- Uptime backend Fly.io: ≥ 99.5%
- Crash-free sessions PWA: ≥ 99%
- Custo APIs/mês: < €8 (Groq + ElevenLabs + Google + Fly.io + Supabase)
- Gmail Push delay (Pub/Sub → UI): < 5s

**V1 declarado "done" quando:** JP usa o Per4Biz diariamente como ferramenta principal de email+calendar+contactos no telemóvel por ≥ 14 dias consecutivos sem voltar a abrir as apps nativas do Google.

---

## 10. Perguntas em aberto (follow-ups)

- Re-consent flow em produção: prompt único ou guiado em passos? **Decisão no S5 planning**
- VAPID keys: geradas manualmente 1× ou automatizado? **Decisão no S7 planning**
- Pub/Sub topic share entre devs ou 1 por ambiente? **1 por ambiente (dev/prod), decidido aqui**
- Bridge threshold de confidence: 0.7 é empírico; afinar em S8 com dados reais
- Métricas em dashboard: Supabase direct queries ou Axiom? **Decisão no S9**

---

## 11. Como este spec interage com outros docs

| Doc | Impacto deste spec |
|---|---|
| `01-prd/PRD-MASTER.md` | §6 RF-9 e RF-10 sobem para V1; RF-2 continua V2 |
| `02-ultraplan/ULTRAPLAN-tecnico.md` | Adicionar 4.x Calendar, 4.y Contacts, 9.x Gmail Push, 9.y Web Push; remover Claude do §2.6 |
| `03-ui-ux/DESIGN-SPEC.md` | Adicionar cards `agenda-event`, `contact-result`, `bridge-suggest` |
| `04-sprints/SPRINT-PLAN.md` | Reescrever Sprints 4-6 como Sprints 4-9 per §5 deste doc |
| `06-addendum/ACCEPTANCE-CRITERIA.md` | Adicionar ACs E7/E8/E9/E10/E11/E12 per §7 deste doc |
| `07-v1-scope/EXECUTION-NOTES.md` | §6 checklist: remover calendar/contacts da lista "não codificar" |

Os docs canónicos serão actualizados como parte do plano de implementação (tarefa 0 do PLAN.md).

---

**Próximo passo:** skill `writing-plans` gera `plans/per4biz-v1-completo/PLAN.md` com tasks bite-sized por sprint.
