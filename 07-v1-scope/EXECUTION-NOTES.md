# V1 Execution Scope — o que implementamos AGORA

**Documento canónico de execução.** Os docs 01-06 descrevem o **produto-alvo**. Este doc descreve **o que está fora do V1 a ser implementado agora**, por decisão do PO (JP) a 2026-04-15.

**Regra de ouro:** o PRD continua válido como visão. Este doc rege o que entra no Sprint 0→6.

---

## 1. Decisões do PO (2026-04-15)

| # | Questão | Decisão |
|---|---|---|
| 1 | Calendar V1.x vs V2 | **V2 definitivo** — não entra nos 13 semanas |
| 2 | Mercado PT vs PT+BR | **PT-PT only** — sem i18n |
| 3 | Transcripts retenção 30d | **Opt-in, default OFF** (recomendação aceite) |
| 4 | Domínio | **`per4biz.vercel.app`** — Vercel default; sem custom domain V1 |
| 5 | Voz TTS | **Feminina PT-PT** — ElevenLabs voice_id a escolher no Sprint 2 |
| 6 | Orçamento CASA | **Não aplicável** — single-tenant, modo "testing" indefinido |
| 7 | Beta-testers | **1 user = JP (self-use)** — sem beta externo em V1 |

---

## 2. Arquitetura alvo mantém-se — execução V1 é subset

### O que o PRD/Ultraplan descreve (target)
Sistema multi-tenant, N utilizadores, cada um com N contas Google, RLS completo, CASA verified, auditado GDPR, com rate limits e consent flows.

### O que V1 executa (self-use)
**1 utilizador (JP) × N contas Google próprias** (V1: 1 conta; V1.x: 2+ contas próprias dele).
- Tabelas têm `user_id` porque a arquitetura suporta multi-tenant (não refactor depois)
- **Mas não implementamos** RLS policies, consent flows, CASA, rate limits, session management complexo

---

## 3. Matriz — target vs V1 execution

| Componente | PRD target (mantém-se) | V1 execução (o que codamos) |
|---|---|---|
| **Supabase Auth** | Magic link + Google OAuth identidade | **Não usar** — identidade = email do `id_token` Google. Se matches `ALLOWED_USER_EMAIL` do env → autorizado. |
| **RLS policies** | `auth.uid() = user_id` em tudo | **Não criar policies** — FastAPI valida `ALLOWED_USER_EMAIL` na entrada e confia daí em diante |
| **`user_id` em todas tabelas** | FK para `auth.users` | **Manter coluna** mas hardcoded para UUID fixo do JP; futuro multi-user é migração trivial |
| **Consent log** | Checkbox GDPR + audit trail | **Skip** — auto-consentimento implícito |
| **CASA Tier 2** | Letter of Assessment auditado | **Skip total** — modo "testing" no Google Cloud Console aceita até 100 utilizadores indefinidamente; JP é 1 |
| **mTLS BFF↔backend** | Shared secret `X-Internal-Auth` | **Skip** — bearer token simples; backend só aceita requests com header do JP |
| **Rate limiting Upstash Redis** | 60 req/min por user, sliding window | **Skip Redis** — cap hardcoded em código se necessário |
| **Push notifications Web Push** | VAPID + Pub/Sub | **Adiar para Sprint 5** ou V1.x — não bloqueia loop de valor |
| **Encryption AES-256-GCM tokens** | Obrigatório | **MANTER** — mesmo single-user, tokens Google cifrados em DB (Fly.io volume) |
| **HTTPS / TLS 1.3** | Obrigatório | **MANTER** — Vercel e Fly.io já fornecem |
| **Groq + Claude split LLM** | ADR-003 | **Apenas Groq** — sem Anthropic key disponível. Llama 3.3 70B Versatile para tudo. |
| **ElevenLabs TTS** | Multilingual v2 streaming | **MANTER** — voz feminina PT-PT (voice_id escolhido Sprint 2) |
| **Supabase Realtime** | Sync cross-device | **Skip** — 1 user, 1 device na prática |
| **Multi-conta Google (2+)** | V1.x, Sprint 4 | **Mantém-se** — 2+ contas do próprio JP |
| **Calendar Google** | V2 | **Fora do Sprint 5** — Sprint 5 revisto |
| **Contacts Google** | V2 | **Fora** |
| **Push notifications** | Sprint 5 V1.x | **Adia para V1.x pós-beta** |
| **Offline fila outbox** | Sprint 6 | **Mantém em V1** — qualidade essencial |

---

## 4. Stack final confirmada para V1

```
[PWA Next.js 16 — Vercel per4biz.vercel.app]
           ↓ HTTPS + bearer token
[FastAPI Python 3.12 — Fly.io Madrid mad]   ← backend obrigatoriamente Python
           ├→ Google APIs (Gmail read+send; Calendar+Contacts V2)
           ├→ Groq (Whisper v3 STT + Llama 3.3 70B intents+drafts)
           ├→ ElevenLabs (TTS feminina PT-PT streaming)
           └→ Supabase (Postgres + Storage — SEM Auth, SEM RLS, SEM Realtime)

Auth identidade = Google OAuth 1× (id_token.email == ALLOWED_USER_EMAIL)
Tokens operacionais Google = AES-256-GCM em Postgres
```

**1 API key cada:** `GROQ_API_KEY`, `ELEVENLABS_API_KEY`, `GOOGLE_CLIENT_ID/SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, `ENCRYPTION_KEY`.

**Não precisa:** Anthropic, Upstash Redis, Sentry (para V1 self-use — podemos adicionar depois).

---

## 5. Sprint Plan revisto

Substituições nos 147 pts originais:

| Sprint | Original | V1 Execution |
|---|---|---|
| **S0** (Semana 1) | Setup & discovery | **Mantém-se** — agora sem OAuth verification (CASA) |
| **S1** (Sem 2-3, 28 pts) | Auth Google + Inbox read-only | **Mantém-se** — simplificado (sem RLS, sem consent) |
| **S2** (Sem 4-5, 26 pts) | Voice Agent MVP | **Mantém-se** — Groq pipeline + ElevenLabs feminina |
| **S3** (Sem 6-7, 27 pts) | Composer Vocal + Envio | **Mantém-se** — milestone V1-alpha |
| **S4** (Sem 8-9, 22 pts) | Multi-conta + Seletor | **Mantém-se** — 2 contas do próprio JP |
| **S5** (Sem 10-11, 24 pts) | ~~Calendar + Push~~ | **REVISTO → "Polish v1 + Push notifications + Onboarding polido"** (20 pts) |
| **S6** (Sem 12-13, 20 pts) | Polish + Beta Launch | **REVISTO → "QA + Performance + Self-use production"** (18 pts) |

**Total revisto:** ~141 pts (antes 147) — pequena folga.

**Sem externo beta:** JP é user-único. "Launch" = JP a usar diariamente.

---

## 6. O que NÃO se codifica em V1 — checklist anti-scope-creep

- [ ] Policies RLS Postgres
- [ ] Supabase Auth flows
- [ ] Consent checkboxes GDPR
- [ ] Consent log table
- [ ] CASA security assessment submission
- [ ] Rate limiting Upstash
- [ ] mTLS / shared secret entre serviços
- [ ] Multi-user signup
- [ ] User management UI
- [ ] Session management complexo (JWT refresh, multi-device)
- [ ] Calendar integration (V2)
- [ ] Contacts integration (V2)
- [ ] Wake word
- [ ] Classificação IA de emails
- [ ] Resumos de thread
- [ ] i18n (PT-BR, EN)

Se um agent Claude começar a implementar algo desta lista → **parar e perguntar ao PO**.

---

## 7. O que SE codifica em V1 — loop mínimo de valor

1. ✅ Login Google simples (1 conta → id_token + refresh_token cifrado)
2. ✅ Inbox unificada (V1: 1 conta; S4: 2+)
3. ✅ Abrir email → ler em voz (ElevenLabs PT-PT feminina)
4. ✅ Push-to-talk → Groq Whisper → Llama 3.3 intent → Llama 3.3 draft
5. ✅ Aprovar draft → enviar via Gmail API
6. ✅ PWA instalável iOS + Android
7. ✅ AES-256-GCM tokens
8. ✅ HTTPS tudo
9. ✅ Offline shell + cache 50 emails
10. ✅ Outbox fila de envio offline

**Se o loop 1→5 funciona ao vivo em < 60s por email → V1 done.**

---

## 8. Como este doc interage com os restantes

| Doc | Status |
|---|---|
| `01-prd/PRD-MASTER.md` | **Inalterado** — visão produto |
| `02-ultraplan/ULTRAPLAN-tecnico.md` | **Inalterado** — arquitetura alvo |
| `03-ui-ux/DESIGN-SPEC.md` | **Inalterado** |
| `04-sprints/SPRINT-PLAN.md` | Sprints 5-6 revistos neste doc §5 (sem tocar no original) |
| `05-validacao/VALIDACAO-INTERNA.md` | 6/7 perguntas resolvidas aqui §1 |
| `06-addendum/*` | **Inalterado** — padrões enterprise continuam como alvo |
| `07-v1-scope/EXECUTION-NOTES.md` | **ESTE DOC** — rege execução V1 |

**Em caso de conflito entre este doc e 01-06 → este doc vence para decisões de código V1.**

---

## 9. Quando sair deste modo

Sair de single-tenant = migrar para multi-tenant. Gatilho:
- JP decide lançar publicamente, OU
- 2º utilizador real quer acesso

**Trabalho estimado para multi-tenant upgrade:** ~2 semanas (1 sprint). Envolve:
- Adicionar Supabase Auth + JWT validation
- Criar RLS policies em cada tabela (`user_id = auth.uid()`)
- Implementar signup + consent flows
- Submeter CASA Tier 2 (6-10 semanas espera + €8-15k)
- Rate limiting Upstash
- UI para user management

Este doc será **arquivado** quando isto acontecer.
