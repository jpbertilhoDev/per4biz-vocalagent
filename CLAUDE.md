# Per4Biz — Instruções para Claude

**Produto:** PWA mobile (iOS/Android) — agente vocal de email multi-conta Google.
**Status:** Pivot chat-first + redesign visual (v2.0). E1-E5 implementados (inbox-first). Redesign em curso.
**Stack:** Next.js 16 PWA + FastAPI Python + Supabase + Groq + ElevenLabs.
**Agente:** Vox — o agente IA é a tela principal (chat-first).

Este ficheiro é lido em cada task. Mantém-te breve e segue as regras abaixo.

---

## 1. Documentos canônicos (lê quando relevante)

| Tópico | Ficheiro |
|---|---|
| PRD mestre (requisitos, escopo V1/V2) | [01-prd/PRD-MASTER.md](01-prd/PRD-MASTER.md) |
| Arquitetura técnica + ADRs + schema SQL | [02-ultraplan/ULTRAPLAN-tecnico.md](02-ultraplan/ULTRAPLAN-tecnico.md) |
| Design system + wireframes + componentes | [03-ui-ux/DESIGN-SPEC.md](03-ui-ux/DESIGN-SPEC.md) |
| Épicos + user stories + roadmap | [04-sprints/SPRINT-PLAN.md](04-sprints/SPRINT-PLAN.md) |
| Validação interna + perguntas ao PO | [05-validacao/VALIDACAO-INTERNA.md](05-validacao/VALIDACAO-INTERNA.md) |
| **Gherkin ACs** (86 critérios em 30 stories) | [06-addendum/ACCEPTANCE-CRITERIA.md](06-addendum/ACCEPTANCE-CRITERIA.md) |
| **Constraints/Assumptions/OOS** (15 CON + 10 ASM + 20 OOS) | [06-addendum/CONSTRAINTS-ASSUMPTIONS-OOS.md](06-addendum/CONSTRAINTS-ASSUMPTIONS-OOS.md) |
| **Error Matrix** (Google API, voice, envio, multi-conta) | [06-addendum/ERROR-MATRIX.md](06-addendum/ERROR-MATRIX.md) |
| **Testing Strategy** (pirâmide unit/integration/E2E + CI) | [06-addendum/TESTING-STRATEGY.md](06-addendum/TESTING-STRATEGY.md) |
| **Logging Policy** (redacção automática, PII zero) | [06-addendum/LOGGING-POLICY.md](06-addendum/LOGGING-POLICY.md) |
| **⚡ V1 Execution Scope** (o que fica fora de V1) | [07-v1-scope/EXECUTION-NOTES.md](07-v1-scope/EXECUTION-NOTES.md) |
| **Design Spec v2.0** (chat-first, dark-first, Vox, Arc+Raycast) | [03-ui-ux/DESIGN-SPEC.md](03-ui-ux/DESIGN-SPEC.md) |

**Regra crítica de execução V1:** Em conflito entre `01-06` (target) e `07-v1-scope/EXECUTION-NOTES.md` (V1) → **vence o V1 scope**. O PRD descreve o futuro; executamos o subset da §7 do EXECUTION-NOTES.
**Regra:** antes de implementar qualquer RF ou user story, lê a secção correspondente do PRD e Ultraplan. Não inventes requisitos.
**Regra Gherkin:** qualquer PR deve listar os ACs cobertos (ex: `Closes AC-E2.US1-3`) — ver [06-addendum/ACCEPTANCE-CRITERIA.md](06-addendum/ACCEPTANCE-CRITERIA.md).

---

## 2. Stack (exato — não improvisar)

**Frontend** (`frontend/`)
- Next.js 16 App Router + `next-pwa` (Workbox)
- TypeScript strict + Tailwind v4 + shadcn/ui
- Zustand (UI state) + TanStack Query (data)
- `@supabase/ssr` + `@supabase/supabase-js`
- Vitest + Playwright (E2E)

**Backend** (`backend/`)
- FastAPI 0.115 + Pydantic v2 + Python 3.12 (**Python obrigatório — decisão PO**)
- `google-api-python-client`, `google-auth-oauthlib`
- **`groq`** (STT Whisper v3 + LLM Llama 3.3 70B — único provider LLM em V1, sem Anthropic)
- `elevenlabs` (TTS feminina PT-PT streaming)
- `supabase` (service_role server-side — DB+Storage apenas, **sem Auth sem RLS em V1**)
- `httpx` + `cryptography` (AES-256-GCM para tokens Google)
- pytest + pytest-asyncio + httpx test client

**Infra**
- Supabase (Postgres + Auth + Storage + Realtime, região EU)
- Upstash Redis (cache + rate limit + queue)
- Vercel (frontend) + Fly.io `mad` (backend)
- Sentry + Axiom (obs)

---

## 3. Regras invioláveis (não-negociáveis em V1)

1. **TDD obrigatório** — RED → GREEN → REFACTOR. Nunca código sem teste a falhar primeiro. Skill `test-driven-development` enforça.
2. **PT-PT** em todas as strings de UI (`pt-PT`, nunca `pt-BR` por defeito).
3. **Nunca logar PII** — emails, corpos, transcripts, tokens. Axiom (quando adicionado) recebe apenas IDs + metadados.
4. **Corpo de email TTL 24h máximo** (`email_cache.body_cached`). Cron de limpeza diário.
5. **Refresh tokens sempre AES-256-GCM** antes de tocar em DB. Chave em `ENCRYPTION_KEY` env.
6. **Multi-conta isolation** — nunca cruzar dados entre `google_account_id` distintos, mesmo do mesmo user.
7. **Confirmação obrigatória antes de enviar email** — nunca `/emails/send` sem user approval explícito.
8. **`ALLOWED_USER_EMAIL` gating** — FastAPI verifica `id_token.email == ALLOWED_USER_EMAIL` em `/auth/google/callback`. Se falhar → 403. Esta é a única barreira de auth em V1.
9. **Backend em Python** — decisão irreversível do PO. Não propor Node/Go/Bun alternatives.
10. **Groq-only LLM** — sem Anthropic key disponível. Tudo passa por `GROQ_API_KEY` (Llama 3.3 70B + Whisper v3).
11. **Chat-first architecture** — Vox é a tela principal. Inbox é tab secundária. Não adicionar features que quebrem este paradigma.
12. **Dark-first only** — sem tema claro em V1. Toda a UI é desenhada para dark `#0A0A0F`.
13. **Violet `#6C5CE7` = UI, Cyan `#00CEFF` = voz** — cores não se misturam nos roles. Cyan é exclusivamente para microfone, waveform, TTS, Vox speaking.
14. **Auto-silêncio 2s** — input de voz para automaticamente após 2s de silêncio. Desactivável em Settings.

**Regras adiadas para multi-tenant upgrade** (ver [07-v1-scope/EXECUTION-NOTES.md](07-v1-scope/EXECUTION-NOTES.md)):
- ~~RLS em toda tabela~~ (não criar policies em V1; `user_id` fica hardcoded para UUID do JP)
- ~~mTLS interno BFF↔FastAPI~~ (bearer simples em V1)
- ~~GDPR consent flows / `DELETE /me` / `GET /me/export`~~ (JP é data subject + controller; implícito)

---

## 4. Comandos (executáveis via Bash tool)

**Frontend** (dentro de `frontend/`)
```bash
npm run dev        # dev server (porta 3000)
npm test           # vitest watch
npm run test:run   # vitest single run (CI)
npm run test:e2e   # playwright
npm run lint       # eslint
npm run typecheck  # tsc --noEmit
npm run build      # produção
```

**Backend** (dentro de `backend/`)
```bash
uv run uvicorn app.main:app --reload  # dev (porta 8000)
uv run pytest                          # tests
uv run pytest -k "test_name"           # test único
uv run ruff check .                    # lint
uv run ruff format .                   # format
uv run mypy app                        # types
```

**Supabase local** (dentro de `supabase/`)
```bash
supabase start                 # local dev DB
supabase migration new <name>  # nova migration
supabase db reset              # reset + rerun migrations
supabase gen types typescript  # gera types para frontend
```

---

## 5. Convenções de diretório

```
Per4Biz/
├── CLAUDE.md                ← este ficheiro
├── README.md
├── 01-prd/ … 05-validacao/  ← docs canônicos (ver §1)
├── Per4Biz-PRD-COMPLETO.{md,pdf}
├── frontend/                ← Next.js 16 PWA (Sprint 0 scaffold)
├── backend/                 ← FastAPI Python (Sprint 0 scaffold)
├── supabase/
│   └── migrations/          ← SQL timestamped
├── specs/                   ← Superpowers: brainstorming outputs
│   └── <feature>/SPEC.md
├── plans/                   ← Superpowers: implementation plans
│   └── <feature>/PLAN.md
├── .env.example             ← template; nunca commitar .env real
└── .gitignore
```

---

## 6. Git

- **Conventional Commits** obrigatório: `feat(scope):`, `fix(scope):`, `chore:`, `docs:`, `refactor:`, `test:`.
- **Scope** normalmente é `frontend`, `backend`, `db`, `voice`, `auth`, `inbox`, `composer`.
- **Branches:** `feat/per4biz-<feature>`, `fix/per4biz-<bug>`. Prefixo `per4biz-` porque vivemos dentro do monorepo `mkt-agency`.
- **Nunca force-push** a `main`. Skill `using-git-worktrees` do Superpowers cria worktrees isolados automaticamente.
- Commit só quando pedido explicitamente.

---

## 7. Workflow Superpowers (como trabalhar com este projeto)

Quando o PO (JP) pedir para implementar algo:

1. **brainstorming** — refinar spec em conversa antes de código. Output → `specs/<feature>/SPEC.md`.
2. **Aprovação do PO** por secções do spec.
3. **using-git-worktrees** — criar worktree `feat/per4biz-<feature>`, rodar setup, baseline verde.
4. **writing-plans** — plan bite-sized (tasks 2-5 min), paths exatos, código completo. Output → `plans/<feature>/PLAN.md`.
5. **subagent-driven-development** — 1 subagent por task, two-stage review (spec compliance + code quality).
6. **test-driven-development** — RED-GREEN-REFACTOR religiosamente em cada task.
7. **requesting-code-review** — entre tasks, blocker em issues críticas.
8. **finishing-a-development-branch** — merge/PR quando tudo verde.

**O agent verifica skills antes de qualquer task.** Não saltar passos.

---

## 8. Estado actual & próximos passos

- ✅ PRD, Ultraplan, Design Spec, Sprint Plan, Validação Interna escritos (2026-04-15).
- ✅ E1-E5 implementados (inbox-first architecture) — auth, inbox, voice reply, send.
- ✅ Repo separado: `github.com/jpbertilhoDev/per4biz-vocalagent`
- ✅ Design Spec v2.0 — pivot chat-first, dark-first, Vox agent, Arc+Raycast visual (2026-04-16).
- ⬜ **Redesign frontend para chat-first** — bottom navbar, chat layout, Vox cards, MicButton.
- ⬜ **Criar SPEC para "chat-first architecture"** em `specs/e6-chat-first-vox/SPEC.md`.
- ⬜ **Atualizar Sprint Plan** para reflectir pivot (chat-first muda prioridades).

---

## 9. O que NÃO fazer

- Não inventar features fora do escopo V1 (ver PRD §6).
- Não usar `gmail.full` scope (rejeita verificação Google).
- Não guardar corpo de email > 24h.
- Não criar abstrações "para o futuro" (YAGNI).
- Não misturar PT-BR com PT-PT em UI.
- Não commit de `.env` real, credenciais ou tokens Google.
- Não saltar TDD porque "é pequeno".
- Não bypasses de hooks (`--no-verify`) sem autorização explícita.
- Não implementar tema claro (dark-first only em V1).
- Não usar cyan `#00CEFF` para nada que não seja voz/áudio.
- Não voltar ao paradigma inbox-first — chat-first é a decisão arquitectural.
