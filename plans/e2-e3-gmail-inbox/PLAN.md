# PLAN — E2+E3 Gmail Inbox (read-only)

**Sprint:** 1.x (completa scope original do Sprint 1) · **Pontos:** 21
**SPEC:** [../../specs/e2-e3-gmail-inbox/SPEC.md](../../specs/e2-e3-gmail-inbox/SPEC.md) (✅ aprovado)
**Status:** ✅ aprovado · **Autor:** JP + Claude · **Data:** 2026-04-15

---

## Sumário

11 tasks em 3 tracks. TDD RED→GREEN em backend, RED→GREEN focado em frontend. Cobre 8 ACs do SPEC §6. ~3h focado.

---

## Pré-requisitos

- [x] Sprint 1 E1 merged (cookie session + SessionMiddleware + current_user dep)
- [x] `email_cache` table criada (migration 0001)
- [x] refresh_token cifrado em `google_accounts` (do primeiro login live)
- [x] `google-api-python-client` + `google-auth` em `backend/pyproject.toml`

---

## Tasks

### Track 1 — Backend Gmail service (Tasks 1-4)

#### Task 1 — RED: Gmail service tests
- **Specialist:** per4biz-qa-tdd
- **AC:** prep para AC-2.1, AC-2.2, AC-2.6, AC-2.7
- **Files:** `backend/tests/test_gmail_service.py`
- **Tests:**
  - `test_list_messages_returns_emails_for_user`
  - `test_get_message_returns_body_html_stripped`
  - `test_access_token_refresh_when_expired`
  - `test_invalid_grant_raises_specific_error`
  - `test_html_to_text_removes_tags_preserves_structure`
- **Mock:** `googleapiclient.discovery.build` + `Credentials` com pytest-mock
- **Alvo:** `app.services.gmail` — funções `list_messages(user_id, page_token=None, limit=50)`, `get_message(user_id, message_id)`, `_get_valid_credentials(user_id)` (privada mas testável)
- **Comando:** `cd backend && uv run pytest tests/test_gmail_service.py -v` → FAIL ModuleNotFoundError

#### Task 2 — GREEN: Gmail service
- **Specialist:** per4biz-backend-python
- **Files:**
  - `backend/app/services/gmail.py`
  - (possível) `backend/app/services/html_to_text.py` — stdlib HTMLParser
- **API:**
  - `list_messages(user_id: str, page_token: str | None = None, limit: int = 50) -> dict`
  - `get_message(user_id: str, message_id: str) -> dict`
- **Flow:**
  1. Fetch `google_accounts` row for `user_id` (primary)
  2. Decrypt `refresh_token_encrypted` + `access_token_encrypted`
  3. Build `google.oauth2.credentials.Credentials(...)` com token, refresh_token, token_uri, client_id, client_secret
  4. Se `credentials.expired`, chama `credentials.refresh(Request())` → salvar novo access_token cifrado + novo expires
  5. `build("gmail", "v1", credentials=credentials)` → `service.users().messages().list(userId="me", maxResults=limit, pageToken=page_token, q="in:inbox")` 
  6. Para cada ID: `service.users().messages().get(userId="me", id=msg_id, format="metadata", metadataHeaders=["From","Subject","Date"])`
  7. Persist metadata em `email_cache` (upsert on `gmail_message_id`)
  8. Return DTO
- **HTML→text:** `_HTMLStripper(HTMLParser)` stdlib, `.get_data()` → normalized whitespace
- **Comando:** `uv run pytest tests/test_gmail_service.py -v` + `ruff` + `mypy`

#### Task 3 — RED: `/emails` endpoints tests
- **Specialist:** per4biz-qa-tdd
- **AC:** AC-2.1, AC-2.2, AC-2.6, AC-2.7, AC-2.8
- **Files:** `backend/tests/test_emails_endpoints.py`
- **Tests:**
  - `test_list_requires_auth` (401 sem cookie)
  - `test_list_returns_emails_happy_path` (com session cookie + mock gmail.list_messages)
  - `test_list_paginates_with_page_token`
  - `test_get_message_requires_auth`
  - `test_get_message_returns_body_text`
  - `test_invalid_grant_returns_401_and_clears_cookie`
  - `test_rate_limit_exceeds_returns_429` (mock redis counter)
- **Comando:** `uv run pytest tests/test_emails_endpoints.py -v` → FAIL

#### Task 4 — GREEN: `/emails` router
- **Specialist:** per4biz-backend-python
- **Files:**
  - `backend/app/routers/emails.py`
  - `backend/app/services/rate_limit.py` (pode ser in-memory stub se Upstash não configurado; real Redis em sprint DevOps)
  - **Editar** `backend/app/main.py` — registar router
- **API:**
  - `GET /emails/list?limit=50&page_token=...` → `current_user` dep → rate_limit check → `gmail.list_messages(user["sub"], ...)` → DTO
  - `GET /emails/{message_id}` → `current_user` dep → `gmail.get_message(user["sub"], message_id)` → DTO
- **Error handling:**
  - `googleapiclient.errors.HttpError(401)` → chamar `google_oauth.revoke_token` (best-effort) + `sb.table("google_accounts").delete()` + response com `Set-Cookie: __Host-session=; Max-Age=0`
  - Rate limit exceeded → `HTTPException(429, headers={"Retry-After": "60"})`
- **Comando:** `uv run pytest tests/ -v` → 45+ passed

---

### Track 2 — Frontend Inbox (Tasks 5-8)

#### Task 5 — GREEN: TanStack Query + API client setup
- **Specialist:** per4biz-frontend-pwa
- **Files:**
  - `frontend/app/providers.tsx` (novo) — `<QueryClientProvider>` wrapper
  - `frontend/app/layout.tsx` — embrulhar children com Providers
  - `frontend/lib/api.ts` — `apiFetch(path, options)` helper com `credentials: "include"` + baseURL = NEXT_PUBLIC_API_URL
  - `frontend/lib/queries.ts` — `listEmails()`, `getEmail(id)` fetchers
- **Não há testes unitários nesta task** (setup infrastrutural); cobertura vem indirecta nos tests de pages
- **Comando:** `npm.cmd run typecheck` → clean

#### Task 6 — RED: inbox list tests + EmailItem tests
- **Specialist:** per4biz-qa-tdd + per4biz-frontend-pwa
- **Files:**
  - `frontend/tests/inbox.test.tsx`
  - `frontend/tests/email-item.test.tsx`
- **Tests:**
  - `renders empty state when no emails`
  - `renders 50 email items`
  - `shows unread indicator for is_unread=true`
  - `clicking item navigates to /email/[id]`
  - `shows error state with retry button on fetch fail`
  - `EmailItem renders from_name, subject, snippet, relative time`
  - `EmailItem shows bullet marker only when is_unread`
- **Mock:** TanStack Query com mock data + `vi.mock("@/lib/queries")` ou MSW
- **Comando:** `npm.cmd run test:run` → falha

#### Task 7 — GREEN: `/inbox` page + EmailItem component
- **Specialist:** per4biz-frontend-pwa + per4biz-ui-ux
- **Files:**
  - `frontend/app/inbox/page.tsx` (client, uses TanStack Query)
  - `frontend/components/email-item.tsx`
  - `frontend/components/email-skeleton.tsx` (3 rows pulsing)
  - `frontend/lib/relative-time.ts` (pt-PT "há 2h", "ontem", "dd MMM")
- **Padrão:**
  - Header sticky com contagem não-lidos
  - Lista scroll infinito (mas só 50 em V1)
  - Loading skeleton durante fetch
  - Error state com botão "Tentar de novo" (PT-PT)
  - Empty state "Sem emails"
- **Comando:** `npm.cmd run test:run && npm.cmd run typecheck`

#### Task 8 — GREEN: `/email/[id]` page + pull-to-refresh
- **Specialist:** per4biz-frontend-pwa + per4biz-ui-ux
- **Files:**
  - `frontend/app/email/[id]/page.tsx` (client, dynamic route)
  - `frontend/components/pull-to-refresh.tsx` (touch gesture handler — simples, sem lib)
  - Possivelmente `frontend/components/back-button.tsx`
- **Pull-to-refresh:** native gesture listen no scrollTop === 0 + threshold 80px → trigger `queryClient.invalidateQueries(["emails", "list"])`
- **Detail page:**
  - Loading skeleton
  - Erro → toast inline
  - Header compacto com back arrow
  - Body text `whitespace-pre-wrap` scrollable
- **Comando:** `npm.cmd run test:run && npm.cmd run typecheck`

---

### Track 3 — E2E & Validation (Task 9)

#### Task 9 — E2E + Checkpoint JP
- **Specialist:** per4biz-qa-tdd
- **Files:** `frontend/tests/e2e/inbox-happy-path.spec.ts`
- **Teste:**
  - Stub backend `/emails/list` e `/emails/:id` via `page.route`
  - Fluxo: mock login cookie → navegar `/inbox` → confirmar 3 items visíveis → click item → URL muda → detail body visível
- **Checkpoint JP:** 🔴 **SIM** — JP testa live:
  1. Backend + Frontend running
  2. Já logado (cookie válido do Sprint 1)
  3. Abre `/inbox` em browser → vê os 50 emails reais
  4. Click num email → `/email/[id]` → vê body
  5. Pull-to-refresh funciona
- **Comando:** `cd frontend && npm.cmd run test:e2e -- inbox` (opcional, se browsers instalados)

---

## Checkpoints

| # | Quando | Critério |
|---|---|---|
| 1 | Após Task 4 | Backend /emails funcional, 45+ tests ✅ |
| 2 | Após Task 9 | Live test JP em browser real com emails reais |

---

## Riscos

| # | Risco | Mitigação |
|---|---|---|
| R-E2.1 | Gmail API rate limit (250 quota units/s) exaustão | In-memory rate limit V1, Upstash Redis Sprint 2 |
| R-E2.2 | HTML emails com CSS inline quebram text extraction | stdlib HTMLParser é conservativo; sanitizar antes de renderizar |
| R-E2.3 | refresh_token Google revogado entre requests | AC-2.7 — detect invalid_grant → clear cookie → re-auth |
| R-E2.4 | Pull-to-refresh sem lib pode dar flicker iOS Safari | Fallback: botão refresh manual visível sempre |
| R-E2.5 | Emails com corpos enormes (MB) congelam UI | Limitar body_text a 100KB truncated em V1 |

---

## Cobertura ACs

| AC | Task |
|---|---|
| AC-2.1 | Tasks 1, 3 |
| AC-2.2 | Tasks 1, 3 |
| AC-2.3 | Tasks 7 |
| AC-2.4 | Task 8 |
| AC-2.5 | Tasks 7, 8 |
| AC-2.6 | Task 2 |
| AC-2.7 | Tasks 2, 4 |
| AC-2.8 | Task 4 |

---

**Fim.**
