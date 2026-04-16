---
description: Orquestra Sprint 1 do Per4Biz (E1 Auth + E2 Gmail stubs). Lança subagents em sequência com checkpoints.
---

# Sprint 1 Kickoff — Per4Biz

## Pré-requisitos (bloqueia se faltar)
1. ✅ SPEC E1 §1-§8 aprovado (`specs/e1-auth-google-oauth/SPEC.md` — checkboxes ✅)
2. ✅ `.env` completo (`ENCRYPTION_KEY` + `INTERNAL_API_SHARED_SECRET` preenchidos)
3. ✅ Migrations 0001-0003 aplicadas em Supabase local (`supabase db reset`)
4. ✅ Perguntas PO §5 VALIDACAO respondidas (transcripts opt-in, Calendar V2)
5. ✅ Worktree criado: `feat/per4biz-e1-auth`

## Formação Sprint 1
- **Lead:** `per4biz-architect`
- **Security:** `per4biz-security-oauth`
- **Backend:** `per4biz-backend-python`
- **Database:** `per4biz-database`
- **Frontend:** `per4biz-frontend-pwa`
- **UI/UX:** `per4biz-ui-ux`
- **QA:** `per4biz-qa-tdd`

## Workflow (sequencial, checkpoint entre tasks)

### Task 1 — Planning
`per4biz-architect` lê SPEC + SPRINT-PLAN e escreve `plans/e1-auth-google-oauth/PLAN.md` com tasks 2-5 min, TDD explícito, paths exatos.

**🔴 CHECKPOINT** — JP revê plano antes de avançar.

### Task 2 — Security foundation (RED)
`per4biz-qa-tdd` escreve testes para `app/services/crypto.py` (AES-256-GCM roundtrip) e `app/services/state_jwt.py` (sign/verify, expiry).

### Task 3 — Security foundation (GREEN)
`per4biz-security-oauth` implementa `crypto.py` + `state_jwt.py`. Testes passam.

### Task 4 — OAuth endpoints (RED)
`per4biz-qa-tdd` escreve testes para `/auth/google/start` e `/auth/google/callback` (happy path + AC-7 CSRF + AC-8 token redaction).

### Task 5 — OAuth endpoints (GREEN)
`per4biz-backend-python` + `per4biz-security-oauth` co-implementam. Testes passam.

### Task 6 — Frontend Welcome (RED + GREEN)
`per4biz-qa-tdd` + `per4biz-frontend-pwa` + `per4biz-ui-ux` colaboram (test → component → PT-PT copy).

### Task 7 — Session persistence
`per4biz-backend-python` + `per4biz-frontend-pwa` — `@supabase/ssr` middleware + cookie `__Host-`.

### Task 8 — E2 Gmail stubs (preparação Sprint 2)
`per4biz-backend-python` cria stubs `/emails/list`, `/emails/{id}` com mocks. `per4biz-architect` review.

**🔴 CHECKPOINT FINAL** — JP revê diff completo antes de commit.

## Regras operacionais
- **Nunca auto-commit** — JP revê e commita
- **TDD em cada task** — sem exceção (CLAUDE.md §3.1)
- **ACs Gherkin** — PR lista `Closes AC-E1.US1-3 AC-E1.US2-1 AC-E1.US4-1`
- **Blockers escalam** — specialist → architect → JP

## Invocação
Invocar este command após os 5 pré-requisitos estarem ticked. O architect pega o bastão e orquestra o resto via Task calls aos specialists.
