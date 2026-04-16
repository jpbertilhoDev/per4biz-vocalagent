# Plano Técnico — Per4Biz

**Projeto:** Per4Biz — Copiloto Pessoal de Email e Agenda com Voz
**Cliente:** JP Bertilho / mkt-agency
**Autor:** Ultraplan (arquiteto técnico)
**Data:** 2026-04-15
**Versão:** 1.0 (arquitetura inicial)
**Status:** Proposta para validação do CTO

---

## 0. Resumo executivo

Per4Biz é um PWA mobile-first que se comporta como um secretário pessoal vocal: o utilizador fala, o sistema executa ações em múltiplas contas Google (Gmail, Calendar, Contacts) e devolve resposta em voz e texto. A arquitetura recomendada é **PWA Next.js 16 (App Router)** + **microserviço Python FastAPI** + **Supabase (Postgres + Auth + Storage)** + **pipeline de voz Groq Whisper → Claude/Groq → ElevenLabs**, com OAuth 2.0 Google multi-conta, criptografia AES-GCM de refresh tokens, e RLS restrita por `user_id`.

---

## 1. Arquitetura Geral

```
                            ┌─────────────────────────────────────┐
                            │          UTILIZADOR (JP)            │
                            │   iPhone / Android (PWA instalado)  │
                            └──────────────┬──────────────────────┘
                                           │ HTTPS + WSS
                                           ▼
              ┌────────────────────────────────────────────────────┐
              │   FRONTEND PWA (Next.js 16, Vercel Edge)           │
              │   - App Shell cache-first (Workbox via next-pwa)   │
              │   - MediaRecorder API (captura de voz)             │
              │   - WebPush / FCM receiver                         │
              │   - Supabase JS SDK (auth session)                 │
              └──────────────┬─────────────────────────────────────┘
                             │ REST + Server Actions + WebSocket
                             ▼
              ┌────────────────────────────────────────────────────┐
              │   API GATEWAY (Next.js Route Handlers - BFF)       │
              │   - Valida sessão Supabase (JWT)                   │
              │   - Orquestra chamadas ao microserviço Python      │
              │   - Rate limiting (Upstash Redis)                  │
              └──────────────┬─────────────────────────────────────┘
                             │ HTTPS mTLS interno (shared secret)
                             ▼
              ┌────────────────────────────────────────────────────┐
              │   MICROSERVIÇO PYTHON (FastAPI, Fly.io)            │
              │   ├── /auth/google (OAuth callback)                │
              │   ├── /emails   (Gmail API)                        │
              │   ├── /calendar (Calendar API)                     │
              │   ├── /contacts (People API)                       │
              │   ├── /voice    (STT + intent + LLM + TTS)         │
              │   └── /sync     (background worker - arq/Celery)   │
              └──────┬──────────────────┬────────────────┬─────────┘
                     │                  │                │
                     ▼                  ▼                ▼
            ┌──────────────┐   ┌──────────────┐  ┌──────────────────┐
            │ Google APIs  │   │ LLM / STT /  │  │   Supabase       │
            │ - Gmail      │   │ TTS vendors  │  │ - Postgres + RLS │
            │ - Calendar   │   │ - Groq       │  │ - Auth (session) │
            │ - People     │   │ - Claude     │  │ - Storage (audio)│
            │              │   │ - ElevenLabs │  │ - Realtime       │
            └──────────────┘   └──────────────┘  └──────────────────┘
                                                        ▲
                                                        │
                                              ┌─────────┴─────────┐
                                              │  Upstash Redis    │
                                              │  - cache emails   │
                                              │  - job queue      │
                                              │  - rate limits    │
                                              └───────────────────┘
```

---

## 2. Stack Tecnológica Recomendada

### 2.1 Frontend PWA — **Next.js 16 App Router** + `next-pwa` (Workbox)

**Recomendação:** Next.js 16 com App Router, Server Components onde possível, Client Components para partes interativas (gravação de voz, lista de emails).

**Justificação contra Vite+React+Workbox puro:**
- O JP já usa Vercel como padrão de deploy → zero fricção.
- App Router permite Server Actions para chamadas autenticadas ao microserviço sem expor API keys no cliente.
- Streaming de resposta do LLM é nativo via React Server Components + `useOptimistic`.
- `next-pwa` (v6+) gera Service Worker Workbox automaticamente com manifest.
- Edge Runtime da Vercel dá latência <50ms em Lisboa/Madrid.

**Pacotes exatos:**
- `next@16.x`
- `next-pwa@6.x` (ou migrar para `@serwist/next` que é o sucessor oficial)
- `@supabase/ssr@0.5.x` + `@supabase/supabase-js@2.x`
- `tailwindcss@4.x` + `shadcn/ui` (radix-ui)
- `zustand@5.x` (estado de UI: conta ativa, modo voz)
- `@tanstack/react-query@5.x` (cache de emails no cliente)
- `react-media-recorder@1.x` ou `MediaRecorder` nativo
- `framer-motion@12.x` (microinterações do agente vocal)

### 2.2 Backend Python — **FastAPI**

**Recomendação:** FastAPI 0.115+ com Pydantic v2, uvicorn workers.

**Justificação contra Flask:**
- Type hints nativos + validação Pydantic → contrato firme com frontend TypeScript.
- `async/await` nativo → essencial para I/O com Google APIs (batch requests) e streaming LLM.
- OpenAPI auto-gerado → gera cliente TypeScript com `openapi-typescript`.
- Flask só faria sentido se houvesse equipa sénior Flask — não é o caso.

**Pacotes exatos:**
- `fastapi==0.115.*`
- `uvicorn[standard]==0.32.*`
- `google-api-python-client==2.150.*`
- `google-auth-oauthlib==1.2.*`
- `anthropic==0.40.*`
- `groq==0.13.*`
- `elevenlabs==1.8.*`
- `supabase==2.10.*` (server-side client com service_role)
- `arq==0.26.*` (worker assíncrono baseado em Redis — mais leve que Celery)
- `cryptography==44.*` (Fernet/AES-GCM para refresh tokens)
- `httpx==0.27.*`

### 2.3 Banco de dados — **Supabase (padrão da casa)**

- Postgres 16
- RLS ativado em todas as tabelas sensíveis
- `pgvector` para embeddings de emails (busca semântica futura)
- Supabase Auth emite JWT consumido pelo FastAPI (via `SUPABASE_JWT_SECRET`)

### 2.4 Autenticação — **Supabase Auth + Google OAuth 2.0 (flow separado)**

**Importante:** o login na app usa Supabase Auth (magic link ou Google OAuth de identidade). A vinculação de **contas operacionais** (as que serão lidas/escritas) usa um **segundo flow OAuth 2.0** separado, com scopes de Gmail/Calendar/Contacts — porque o utilizador pode vincular 2, 3, N contas Google distintas da conta de login.

**Armazenamento de refresh tokens:**
- Coluna `refresh_token_encrypted BYTEA` cifrada com **AES-256-GCM**.
- Chave mestra em variável de ambiente (`ENCRYPTION_KEY`) gerida pelo Fly.io Secrets.
- Rotação de chaves via `key_version` na tabela.

### 2.5 Voice / STT — **Groq Whisper Large v3**

**Recomendação:** Groq (Whisper large-v3) como principal, OpenAI Whisper como fallback.

| Opção | Latência | Custo / min | Português PT | Veredicto |
|---|---|---|---|---|
| Groq Whisper v3 | ~200-400ms | ~$0.0001 | Excelente | **Vencedor** |
| OpenAI Whisper | ~1-2s | $0.006 | Excelente | Fallback |
| Google Speech-to-Text | ~500ms | $0.016 | Bom | Caro |

Groq roda Whisper em LPUs com latência ~10x menor que OpenAI pelo mesmo modelo. Para PT-PT o Whisper v3 tem excelente performance.

### 2.6 LLM — **Claude 3.5 Sonnet (drafts) + Groq Llama 3.3 70B (intents)**

**Split estratégico:**
- **Intent classification + ações rápidas** (ex: "lê os últimos 3 emails") → **Groq Llama 3.3 70B** (<500ms, barato).
- **Drafts de email** (tom, idioma PT-PT correto, contexto de thread) → **Claude 3.5 Sonnet** (qualidade superior de escrita PT, melhor controlo de tom profissional).
- **Fallback de drafts** → GPT-4o-mini se Claude indisponível.

### 2.7 TTS — **ElevenLabs (multilingual v2)**

| Opção | Qualidade PT-PT | Latência | Custo |
|---|---|---|---|
| ElevenLabs Multilingual v2 | Excelente (voz PT) | ~400ms (streaming) | $$ |
| Google TTS Wavenet | Bom | ~300ms | $ |
| Web Speech API nativa | Razoável (iOS) / Má (Android) | 0ms | Grátis |

**Recomendação:** ElevenLabs como principal (streaming via WebSocket), Web Speech API nativa como fallback offline/degradado. Usar voz personalizada clonada (4h de gravação do JP ou persona "Per4Biz") para branding forte.

### 2.8 Deploy

- **Frontend:** Vercel (Hobby inicialmente, Pro a partir de 10 utilizadores)
- **Microserviço Python:** **Fly.io** (região `mad` — Madrid, mais próxima de Lisboa que Railway EU). Alternativa: Render (menos performático em EU-South).
- **Redis:** Upstash (serverless, tier free generoso)
- **Monitorização:** Sentry + Axiom (logs estruturados)

### 2.9 Sync de Emails — **Gmail Push Notifications (Pub/Sub) + fallback polling**

- Principal: **Gmail API `watch()` + Google Cloud Pub/Sub** → webhook no FastAPI → invalida cache.
- Fallback: **polling** a cada 2 min via worker `arq` se Pub/Sub falhar.
- Redis/BullMQ-equivalente em Python = **arq** (mais leve, async-native).

---

## 3. Modelo de Dados (Supabase / Postgres)

```sql
-- 1. users (estende auth.users do Supabase)
users (
  id UUID PK REFERENCES auth.users(id),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  preferred_language TEXT DEFAULT 'pt-PT',
  voice_id TEXT,              -- ElevenLabs voice preference
  active_account_id UUID,     -- FK para google_accounts
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- 2. google_accounts (N contas por user)
google_accounts (
  id UUID PK,
  user_id UUID FK -> users(id) ON DELETE CASCADE,
  google_email TEXT NOT NULL,
  display_name TEXT,          -- ex: "Pessoal", "mkt-agency"
  color_hex TEXT DEFAULT '#3B82F6',
  refresh_token_encrypted BYTEA NOT NULL,
  access_token_encrypted BYTEA,
  access_token_expires_at TIMESTAMPTZ,
  scopes TEXT[],
  key_version INT DEFAULT 1,
  last_sync_at TIMESTAMPTZ,
  pubsub_watch_expiration TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ,
  UNIQUE(user_id, google_email)
)

-- 3. email_cache (TTL curto, apenas metadados + snippet)
email_cache (
  id UUID PK,
  google_account_id UUID FK -> google_accounts(id) ON DELETE CASCADE,
  gmail_message_id TEXT NOT NULL,
  thread_id TEXT,
  from_email TEXT,
  from_name TEXT,
  to_emails TEXT[],
  subject TEXT,
  snippet TEXT,               -- 200 chars preview apenas
  body_cached TEXT,           -- full body, APAGA em 24h via cron
  received_at TIMESTAMPTZ,
  is_read BOOLEAN,
  is_starred BOOLEAN,
  labels TEXT[],
  cache_expires_at TIMESTAMPTZ DEFAULT now() + interval '24 hours',
  UNIQUE(google_account_id, gmail_message_id)
)

-- 4. draft_responses (rascunhos gerados pelo agente)
draft_responses (
  id UUID PK,
  user_id UUID FK -> users(id),
  google_account_id UUID FK -> google_accounts(id),
  reply_to_message_id TEXT,   -- gmail_message_id ao qual responde
  subject TEXT,
  body_text TEXT,
  tone TEXT,                  -- 'formal' | 'casual' | 'concise'
  llm_model TEXT,             -- 'claude-3.5-sonnet' etc
  status TEXT,                -- 'draft' | 'approved' | 'sent' | 'discarded'
  voice_session_id UUID FK -> voice_sessions(id),
  created_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ
)

-- 5. voice_sessions (histórico curto de conversas)
voice_sessions (
  id UUID PK,
  user_id UUID FK -> users(id),
  google_account_id UUID FK -> google_accounts(id),
  audio_url TEXT,             -- Supabase Storage, apagado em 7 dias
  transcript TEXT,
  intent TEXT,                -- 'read_inbox' | 'reply_email' | ...
  llm_response TEXT,
  tts_audio_url TEXT,
  duration_ms INT,
  created_at TIMESTAMPTZ
)

-- 6. app_settings (preferências por utilizador)
app_settings (
  user_id UUID PK FK -> users(id),
  default_tone TEXT DEFAULT 'profissional_cordial',
  signature_text TEXT,
  push_notifications_enabled BOOLEAN DEFAULT true,
  wake_word_enabled BOOLEAN DEFAULT false,
  voice_speed FLOAT DEFAULT 1.0,
  auto_sync_interval_sec INT DEFAULT 120,
  unified_inbox BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Índices críticos
CREATE INDEX idx_email_cache_account_received ON email_cache(google_account_id, received_at DESC);
CREATE INDEX idx_email_cache_expiry ON email_cache(cache_expires_at);
CREATE INDEX idx_drafts_user_status ON draft_responses(user_id, status);

-- RLS (exemplo crítico)
ALTER TABLE google_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_accounts" ON google_accounts
  FOR ALL USING (auth.uid() = user_id);
```

---

## 4. Integração Google APIs (Microserviço Python)

### 4.1 Scopes OAuth 2.0 mínimos

```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.modify        (marcar como lido, labels)
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/contacts.readonly
openid email profile
```

Evitar `gmail.full` — Google pode rejeitar a app na verificação. Usar incremental authorization.

### 4.2 Flow OAuth

1. Frontend chama `POST /auth/google/start` → FastAPI devolve URL Google OAuth com `state` assinado (JWT contendo `user_id` + nonce).
2. Google redireciona para `/auth/google/callback` no FastAPI.
3. FastAPI troca `code` por `refresh_token`, cifra, insere em `google_accounts`.
4. Redireciona para `PWA/settings/accounts?connected=1`.

### 4.3 Refresh token storage

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_token(plaintext: str, key: bytes) -> bytes:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return nonce + ct
```

Chave mestra em `fly secrets set ENCRYPTION_KEY=...`.

### 4.4 Endpoints REST internos

| Método | Path | Função |
|---|---|---|
| GET | `/accounts` | Lista contas Google do user |
| POST | `/accounts/link` | Inicia OAuth |
| DELETE | `/accounts/{id}` | Revoga token Google + apaga |
| GET | `/emails?account_id=&limit=20&cursor=` | Lista inbox (usa cache) |
| GET | `/emails/{message_id}` | Email completo (1h cache) |
| POST | `/emails/draft` | Gera draft via LLM |
| POST | `/emails/send` | Envia email |
| GET | `/calendar/events?from=&to=` | Eventos |
| POST | `/calendar/events` | Cria evento |
| GET | `/contacts/search?q=` | Busca contatos |
| POST | `/voice/process` | Pipeline STT → intent → action → TTS |
| POST | `/webhooks/gmail-push` | Pub/Sub notification |

### 4.5 Rate limits e caching

- Gmail API: 1 bilhão quota units/dia (folga para 1 user).
- Por user: limite interno 60 req/min via Upstash Redis (`ratelimit` key pattern).
- Cache de lista de emails em Redis: TTL 60s.
- Cache de corpo de email em Redis: TTL 1h (depois Postgres `email_cache.body_cached` com TTL 24h).
- Batch requests Gmail (`batch.add()`) para carregar 20 emails em 1 round-trip.

---

## 5. Arquitetura do Voice Agent

### 5.1 Pipeline (push-to-talk recomendado)

```
[1] Utilizador carrega no botão do microfone (toque longo)
    ↓
[2] MediaRecorder captura audio/webm;codecs=opus @ 16kHz
    ↓
[3] Ao soltar, blob enviado via POST multipart para /voice/process
    ↓
[4] FastAPI → Groq Whisper v3 (transcrição ~300ms)
    ↓
[5] Intent classifier: Groq Llama 3.3 70B com function calling
       intents: read_inbox | reply_email | compose_email | check_calendar
                create_event | search_contact | switch_account
    ↓
[6] Router executa ferramenta (chama endpoints Gmail/Calendar)
    ↓
[7] LLM gera resposta textual em PT-PT (Claude para drafts, Groq para respostas curtas)
    ↓
[8] ElevenLabs TTS streaming via WebSocket
    ↓
[9] Frontend recebe chunks de audio/mpeg e toca com MediaSource API
```

### 5.2 Wake word vs push-to-talk

**Recomendação: push-to-talk na v1.**

**Razões:**
- Wake word on-device em PWA é tecnicamente pobre (iOS bloqueia mic em background).
- Porcupine (Picovoice) browser SDK existe mas consome bateria e é pouco fiável em mobile web.
- Push-to-talk é convenção universal (tipo walkie-talkie) — zero fricção e 100% fiável.
- Na v2 avaliar Porcupine Web SDK para modo "carro" com wake word "Per4Biz".

### 5.3 Contexto de conversa (memória curta)

- Sessão `voice_session_id` agrupa turnos num período de 5 min.
- Últimos 6 turnos enviados como `messages[]` ao LLM (janela ~2k tokens).
- Após 5 min de inatividade → nova sessão.
- Persistência em `voice_sessions` apenas transcript + intent (não o áudio, que expira em 7 dias no Storage).

### 5.4 Validação por voz/toque

Quando o agente gera um draft:
- UI mostra card com texto do draft.
- Botões: **"Enviar"**, **"Editar"**, **"Descartar"**.
- Comando voz: **"envia"**, **"edita"**, **"não envies"** — NLU simples via regex + LLM fallback.
- Confirmação obrigatória antes de `/emails/send` — evitar envio acidental.

---

## 6. Segurança e Privacidade

Emails pessoais são dado de categoria alta. Tratamento obrigatório.

### 6.1 Criptografia

- **At rest:** Refresh/access tokens cifrados com AES-256-GCM, chave no Fly Secrets.
- **In transit:** HTTPS TLS 1.3 obrigatório; mTLS entre Next.js BFF e FastAPI (shared secret header `X-Internal-Auth`).
- Supabase Storage: buckets privados, signed URLs com TTL 5 min para áudio.

### 6.2 Retenção mínima de conteúdo

- **Corpo de email** nunca armazenado permanentemente. Cache `email_cache.body_cached` com `cache_expires_at = now() + 24h`. Cron job Supabase Edge Function limpa diariamente.
- **Áudio do utilizador:** apagar em 7 dias (cron em `voice_sessions.audio_url`).
- **Transcripts:** mantidos 30 dias para melhoria (opcional e com consentimento).

### 6.3 RLS Supabase

Todas as tabelas com `user_id` têm RLS:

```sql
CREATE POLICY "tenant_isolation" ON {tabela}
  FOR ALL USING (auth.uid() = user_id);
```

FastAPI usa `service_role` key — obrigado a aplicar `user_id` explícito em cada query (nunca confiar no caller).

### 6.4 GDPR / Portugal / UE

- **Consentimento explícito** no primeiro login com checkbox + link para política de privacidade PT.
- **DPA (Data Processing Agreement) com Google** — Google Workspace oferece automaticamente para apps OAuth verificadas.
- **Verificação Google OAuth** obrigatória antes de passar de "testing" para "production" (processo de 4-6 semanas com security assessment CASA para scopes restritos de Gmail).
- **Direito ao esquecimento:** endpoint `DELETE /me` revoga todos os tokens Google + apaga cascata em Supabase.
- **Exportação de dados:** endpoint `GET /me/export` devolve JSON com dados do user.
- **Localização dos dados:** Supabase projeto em `eu-west-3` (Paris) ou `eu-central-1` (Frankfurt) — nunca US.
- **Registo de atividade** (access log) por 90 dias em Axiom.

---

## 7. Suporte Multi-Conta

### 7.1 Troca de conta ativa

- Dropdown no topbar do PWA (avatar + chevron).
- Click → abre sheet com lista de contas + cor/label + toggle "Inbox unificada".
- State global em Zustand: `activeAccountId`.
- Preferência persistida em `users.active_account_id`.
- Hotkey de voz: "muda para conta pessoal" / "switch to agency".

### 7.2 Inbox unificada vs separada

Ambos os modos, utilizador escolhe:

- **Unificada** (default): query agregada `SELECT * FROM email_cache WHERE google_account_id IN (...user accounts)` ordenado por `received_at`. Cada email exibe badge de cor da conta.
- **Separada:** filtro por `active_account_id`.

### 7.3 Identidade visual

- Cada conta tem `color_hex` (default pool: azul, verde, púrpura, laranja).
- Avatar circular com inicial + cor.
- Ao responder, header do draft mostra claramente "A responder de: [cor + email]" — evita erros de envio da conta errada.

---

## 8. PWA Specifics

### 8.1 Service Worker Strategy (Workbox via next-pwa)

```
- App shell (/, /_next/static/*):  CacheFirst (1 ano)
- /api/emails*:                     NetworkFirst, fallback cache 5 min
- /api/calendar*:                   NetworkFirst, fallback cache 10 min
- Áudio blobs:                      NetworkOnly (nunca cache)
- Ícones/manifest:                  CacheFirst
```

### 8.2 Push Notifications

- **Web Push API** (VAPID keys) via biblioteca `web-push` do lado Python.
- iOS Safari suporta Web Push desde iOS 16.4 (requer PWA instalado).
- Android: Web Push nativo OU FCM como fallback.
- Evento: novo email recebido → Pub/Sub → FastAPI → `web-push` para endpoint subscrito.
- Payload mínimo (sem corpo de email): "Novo email de {sender} - {subject}".

### 8.3 Offline mode

- **Funciona offline:**
  - Shell do app (UI estática)
  - Últimos 50 emails cacheados (leitura)
  - Últimos 20 eventos do calendário
  - Escrever drafts em localStorage (IndexedDB via `idb`) → sync quando online (background sync API).
- **NÃO funciona offline:**
  - Voice agent (requer STT/LLM/TTS cloud)
  - Envio de emails (entra em fila local `outbox` e envia ao voltar online)

### 8.4 manifest.json

```json
{
  "name": "Per4Biz",
  "short_name": "Per4Biz",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#0A0A0A",
  "theme_color": "#3B82F6",
  "icons": [
    { "src": "/icons/192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/maskable-512.png", "sizes": "512x512", "purpose": "maskable" }
  ],
  "shortcuts": [
    { "name": "Novo email por voz", "url": "/voice?intent=compose" },
    { "name": "Ler inbox", "url": "/voice?intent=read_inbox" }
  ],
  "share_target": { "action": "/share", "method": "POST" }
}
```

---

## 9. Riscos Técnicos Top 5 e Mitigações

| # | Risco | Impacto | Mitigação |
|---|---|---|---|
| 1 | **Verificação Google OAuth para scopes Gmail restritos pode demorar 4-6 semanas e exigir CASA security assessment (~$15k se terceirizado)** | Lançamento bloqueado | Começar verificação no dia 1. Usar modo "testing" com 100 utilizadores para MVP. Orçamentar auditoria CASA (Letter of Assessment) — fornecedores: Bishop Fox, Leviathan. |
| 2 | **Latência total do pipeline de voz >3s degrada UX** | Produto inutilizável | Target <1.5s end-to-end. Usar Groq (STT+LLM) + ElevenLabs streaming. Medir P95 em Sentry. Fallback: Web Speech API nativa se pipeline cloud falha. |
| 3 | **Custos de LLM/TTS escalam linearmente com uso** | Margem negativa | Cap de 200 interações voz/user/dia. Claude só para drafts (não para respostas triviais). ElevenLabs character cap; usar voz nativa para respostas curtas ("ok", "enviado"). Monitorizar $/user/mês, alerta a $5. |
| 4 | **iOS Safari tem restrições agressivas de mic e background** | PWA sente-se frágil em iPhone | Push-to-talk explícito (não background listening). Instrução clara "instala na tela inicial" (detectar `navigator.standalone`). Testar em iOS real semanalmente. |
| 5 | **Vazamento de refresh tokens = acesso total ao Gmail do user** | Incidente crítico de privacidade | AES-GCM at rest + Fly secrets. Rotação trimestral da chave mestra (`key_version`). Revogar token no Google ao `DELETE /accounts/{id}`. Audit log de todos os acessos a tokens. 2FA obrigatório na Supabase Auth. |

---

## 10. Decisões Arquiteturais (ADR resumidos)

### ADR-001: Next.js 16 App Router em vez de Vite+React
**Contexto:** Precisamos de PWA instalável com SSR/Edge e padrão Vercel.
**Decisão:** Next.js 16 com `next-pwa`/Serwist.
**Consequência:** Server Actions eliminam camada BFF custom; trade-off é lock-in Vercel (aceitável).

### ADR-002: FastAPI em vez de Flask para microserviço Python
**Contexto:** Precisamos de async I/O (Google APIs + LLM streaming) e contrato forte.
**Decisão:** FastAPI + Pydantic v2.
**Consequência:** OpenAPI auto-gerado vira cliente TypeScript; async dá 3-5x throughput em I/O.

### ADR-003: Dois providers LLM — Groq (velocidade) + Claude (qualidade de escrita PT)
**Contexto:** Intents rápidos vs drafts de qualidade.
**Decisão:** Router interno decide: intent classification → Groq Llama 3.3; drafts → Claude 3.5 Sonnet.
**Consequência:** Duas keys/cotas a gerir; ganho: 70% redução de custo em interações simples, qualidade PT-PT superior em drafts.

### ADR-004: Push-to-talk em vez de wake word na v1
**Contexto:** iOS PWA tem limitações severas de mic contínuo.
**Decisão:** PTT na v1; wake word via Porcupine na v2 se houver pedido.
**Consequência:** UX mais pobre que "hey agent" mas 100% fiável cross-browser.

### ADR-005: Nunca armazenar corpo de email além de 24h
**Contexto:** Emails são dado sensível; GDPR e minimização.
**Decisão:** `email_cache.body_cached` com TTL 24h + cron de limpeza; só metadados persistentes.
**Consequência:** Re-fetch ao Gmail se user relê email antigo (trade-off aceitável pelo ganho em privacidade e resposta a pedidos GDPR).

### ADR-006: Fly.io (Madrid) em vez de Railway/Render para microserviço
**Contexto:** Latência para utilizador em Portugal; proximidade do Supabase EU.
**Decisão:** Fly.io região `mad`, auto-scale 1-3 máquinas (shared-cpu-1x, 512MB).
**Consequência:** Custo inicial ~$5/mês; latência Lisboa→Madrid ~15ms vs ~80ms para us-east. Reversível se Fly.io falhar — Dockerfile standard.

---

## 11. Roadmap sugerido

- **Sprint 1-2 (2 semanas):** Setup Next.js + Supabase + FastAPI skeleton. OAuth Google com 1 conta. Listar emails.
- **Sprint 3-4:** Multi-conta. Inbox unificada. Drafts com Claude.
- **Sprint 5-6:** Voice pipeline end-to-end (STT → LLM → TTS). Push-to-talk.
- **Sprint 7:** Calendar + Contacts. Push notifications.
- **Sprint 8:** Hardening (RLS audit, rate limits, Sentry), PWA polish, submissão verificação Google OAuth.

---

## Ficheiros Críticos de Implementação

Os ficheiros abaixo ainda não existem — são os que devem ser criados primeiro:

- `clientes/Per4Biz/frontend/next.config.mjs`
- `clientes/Per4Biz/frontend/app/layout.tsx`
- `clientes/Per4Biz/backend/app/main.py`
- `clientes/Per4Biz/backend/app/integrations/google_oauth.py`
- `clientes/Per4Biz/supabase/migrations/0001_initial_schema.sql`
