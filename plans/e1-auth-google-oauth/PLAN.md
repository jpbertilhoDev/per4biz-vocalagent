# PLAN — E1 Autenticação & Google OAuth

**Sprint:** 1 · **Épico:** E1 · **Pontos:** 13
**SPEC:** [../../specs/e1-auth-google-oauth/SPEC.md](../../specs/e1-auth-google-oauth/SPEC.md) (✅ aprovado com amendments A-E)
**Status:** 🟡 aguarda aprovação do PO (Checkpoint 0)
**Autor:** per4biz-architect · **Data:** 2026-04-15

---

## Sumário executivo

Entrega o gateway de autenticação: login Google → gating `ALLOWED_USER_EMAIL` → tokens cifrados AES-256-GCM → session JWT 7d → trilogia GDPR (revoke + export + delete). **19 tasks** em 6 tracks, **~4-5h de trabalho focado** de specialists. TDD rigoroso (RED antes de GREEN). **4 checkpoints JP** — zero auto-commit. Cobre **8 ACs Gherkin** do SPEC §7.

---

## Pré-requisitos (bloqueia Task 1)

- [x] `.env` completo (ENCRYPTION_KEY, INTERNAL_API_SHARED_SECRET, GOOGLE_*, SUPABASE_*, GROQ_*, ELEVENLABS_*, ALLOWED_USER_EMAIL, USER_ID)
- [x] SPEC E1 aprovado com amendments A-E
- [x] `backend/app/config.py` Pydantic Settings fail-fast
- [x] 9 specialist agents em `.claude/agents/per4biz-*.md`
- [ ] **Migrations 0001-0004 aplicadas em Supabase cloud** (JP aplica via SQL Editor antes de Task 8)
- [ ] **Google Cloud Console:** OAuth 2.0 Client ID criado + redirect URI `http://localhost:8000/auth/google/callback` adicionado + consent screen em modo "Testing" com JP como test user
- [ ] **Checkpoint 0 — JP aprova este PLAN**

---

## Tasks

### Track 1 — Infra Foundation (Tasks 1-6)

#### Task 1 — RED: crypto service tests
- **Specialist:** per4biz-qa-tdd
- **AC coberto:** suporte AC-1 (AES encrypt), AC-8 (tokens never logged)
- **Fase TDD:** RED · **Estimativa:** 5min
- **Files:**
  - `backend/tests/__init__.py` (vazio)
  - `backend/tests/conftest.py` (fixture `settings` override com ENCRYPTION_KEY dummy)
  - `backend/tests/test_crypto.py`
- **Detalhe:** Testes pytest-asyncio para `app.services.crypto`:
  - `test_encrypt_decrypt_roundtrip()` valor entra e sai intacto
  - `test_encrypt_uses_unique_nonce()` 2 chamadas mesmo input → ciphertext diferente
  - `test_decrypt_fails_on_tampered_ciphertext()` flip byte → `InvalidTag`
  - `test_decrypt_fails_on_wrong_key_version()` v2 não decifra v1
  - `test_encryption_key_loaded_from_settings()` usa `get_settings().ENCRYPTION_KEY`
- **Comando:** `cd backend && uv run pytest tests/test_crypto.py -v` (deve FALHAR com ModuleNotFoundError)
- **Checkpoint JP:** não

#### Task 2 — GREEN: crypto service
- **Specialist:** per4biz-security-oauth
- **Fase TDD:** GREEN · **Estimativa:** 10min
- **Files:**
  - `backend/app/__init__.py`
  - `backend/app/services/__init__.py`
  - `backend/app/services/crypto.py`
- **Detalhe:** Implementa `encrypt(plaintext: bytes) -> bytes` e `decrypt(ciphertext: bytes) -> bytes` usando `cryptography.hazmat.primitives.ciphers.aead.AESGCM`. Formato: `key_version(1 byte) || nonce(12) || ct_with_tag(...)`. Chave via `base64.b64decode(get_settings().ENCRYPTION_KEY)` (32 bytes).
- **Comando:** `cd backend && uv run pytest tests/test_crypto.py -v && uv run mypy app/services/crypto.py` (tudo ✅)
- **Checkpoint JP:** não

#### Task 3 — RED: state JWT service tests
- **Specialist:** per4biz-qa-tdd
- **AC coberto:** AC-7 (CSRF)
- **Fase TDD:** RED · **Estimativa:** 5min
- **Files:**
  - `backend/tests/test_state_jwt.py`
- **Detalhe:** Testes para `app.services.state_jwt`:
  - `test_sign_and_verify_roundtrip()` nonce + redirect_to preservados
  - `test_verify_fails_on_tamper()` payload modificado → falha
  - `test_verify_fails_on_expired()` exp < now → falha
  - `test_verify_fails_on_wrong_secret()` secret diferente → falha
  - `test_sign_sets_exp_10min()` exp = iat + 600s
- **Comando:** `cd backend && uv run pytest tests/test_state_jwt.py -v` (FALHA)
- **Checkpoint JP:** não

#### Task 4 — GREEN: state JWT service
- **Specialist:** per4biz-security-oauth
- **Fase TDD:** GREEN · **Estimativa:** 8min
- **Files:**
  - `backend/app/services/state_jwt.py`
- **Detalhe:** `sign_state(redirect_to: str) -> str` e `verify_state(token: str) -> dict`. Usa `python-jose[cryptography]` com HS256. Payload: `{nonce: uuid4(), redirect_to, iat, exp: iat+600}`. Secret: `get_settings().INTERNAL_API_SHARED_SECRET`.
- **Comando:** `cd backend && uv run pytest tests/test_state_jwt.py -v && uv run mypy app/services/state_jwt.py`
- **Checkpoint JP:** não

#### Task 5 — RED: session JWT service tests
- **Specialist:** per4biz-qa-tdd
- **AC coberto:** AC-3 (session persiste)
- **Fase TDD:** RED · **Estimativa:** 5min
- **Files:**
  - `backend/tests/test_session_jwt.py`
- **Detalhe:** Testes para `app.services.session_jwt`:
  - `test_issue_and_decode_roundtrip()` user_id + email preservados
  - `test_session_exp_7d()` exp = iat + 7*86400
  - `test_decode_rejects_expired()`
  - `test_renew_extends_exp_without_reissuing_on_stable_window()` se iat < 6d, devolve mesmo token
  - `test_renew_reissues_when_near_expiry()` se iat > 6d → novo token
- **Comando:** `cd backend && uv run pytest tests/test_session_jwt.py -v` (FALHA)
- **Checkpoint JP:** não

#### Task 6 — GREEN: session JWT service
- **Specialist:** per4biz-security-oauth + per4biz-backend-python
- **Fase TDD:** GREEN · **Estimativa:** 10min
- **Files:**
  - `backend/app/services/session_jwt.py`
- **Detalhe:** `issue_session(user_id: UUID, email: str) -> str`, `decode_session(token: str) -> SessionPayload`, `maybe_renew(token: str) -> str | None`. HS256 com `INTERNAL_API_SHARED_SECRET`. Claims: `sub` (user_id), `email`, `iat`, `exp` (7 dias).
- **Comando:** `cd backend && uv run pytest tests/test_session_jwt.py -v && uv run mypy app/services/session_jwt.py`
- **Checkpoint JP:** 🔴 **sim (Checkpoint 1)** — infra foundation completa; JP revê diff, aprova track 2

---

### Track 2 — OAuth endpoints (Tasks 7-9)

#### Task 7 — RED: auth endpoints tests
- **Specialist:** per4biz-qa-tdd
- **AC coberto:** AC-1, AC-2, AC-7, AC-8 + ALLOWED_USER_EMAIL gating
- **Fase TDD:** RED · **Estimativa:** 15min
- **Files:**
  - `backend/tests/test_auth_endpoints.py`
  - `backend/tests/fixtures/google_oauth_mocks.py` (httpx_mock fixtures para `/token` e `/userinfo`)
- **Detalhe:** Usa `fastapi.testclient.TestClient`. Testes:
  - `test_start_redirects_to_google_with_state()` (AC-1 happy path início)
  - `test_callback_happy_path_creates_accounts_rows()` (AC-1 completo) — mock Google `/token` + `/userinfo`
  - `test_callback_rejects_mismatched_email()` (gating ALLOWED_USER_EMAIL → 403)
  - `test_callback_rejects_invalid_state()` (AC-7 CSRF → 400)
  - `test_callback_encrypts_refresh_token()` (verifica `refresh_token_encrypted` não é plaintext)
  - `test_callback_inserts_consent_log_row()` (privacy-v1.0)
  - `test_logs_never_contain_tokens()` (AC-8 — usa `caplog`, grep `refresh_token`/`access_token`)
  - `test_callback_cancel_redirects_home()` (AC-2)
- **Comando:** `cd backend && uv run pytest tests/test_auth_endpoints.py -v` (FALHA)
- **Checkpoint JP:** não

#### Task 8 — GREEN: OAuth endpoints
- **Specialist:** per4biz-backend-python + per4biz-security-oauth
- **Fase TDD:** GREEN · **Estimativa:** 25min
- **Files:**
  - `backend/app/routers/__init__.py`
  - `backend/app/routers/auth.py` (GET `/auth/google/start`, GET `/auth/google/callback`)
  - `backend/app/services/google_oauth.py` (exchange code → tokens; fetch userinfo)
  - `backend/app/services/supabase_client.py` (helper `get_supabase_admin()` com service_role)
  - `backend/app/main.py` — registar `auth.router`
- **Detalhe:** `/auth/google/start` gera state JWT e redireciona para Google. `/auth/google/callback` valida state, troca code por tokens, verifica `id_token.email == ALLOWED_USER_EMAIL` (senão 403), cifra tokens, upsert em `public.users` + `public.google_accounts` + `public.consent_log`, emite session cookie `__Host-session`, redireciona para `/inbox`.
- **Comando:** `cd backend && uv run pytest tests/test_auth_endpoints.py -v && uv run ruff check . && uv run mypy app`
- **Checkpoint JP:** não

#### Task 9 — REFACTOR: structured logging com PII redactor
- **Specialist:** per4biz-backend-python
- **AC coberto:** AC-8
- **Fase TDD:** REFACTOR · **Estimativa:** 12min
- **Files:**
  - `backend/app/logging.py`
  - `backend/app/main.py` (configurar structlog no startup)
  - `backend/tests/test_logging_redactor.py` (novo teste RED→GREEN confirmando regex redacta tokens)
- **Detalhe:** Processor structlog que redacta via regex `(?i)(token|secret|key|authorization|password|refresh|access)` → `"***"`. Incluir também emails (`[\w.+-]+@[\w-]+\.\w+` → `"***@***"`) exceto `email` em contexto de consent. JSON output em produção, console em dev.
- **Comando:** `cd backend && uv run pytest -k "logging or redactor" -v`
- **Checkpoint JP:** não

---

### Track 3 — Session middleware (Tasks 10-11)

#### Task 10 — RED: session middleware tests
- **Specialist:** per4biz-qa-tdd
- **AC coberto:** AC-3 (persist), AC-6 (invalid_grant → re-login)
- **Fase TDD:** RED · **Estimativa:** 5min
- **Files:**
  - `backend/tests/test_session_middleware.py`
- **Detalhe:** Testes:
  - `test_missing_cookie_returns_401_on_protected_route()`
  - `test_valid_cookie_injects_current_user()`
  - `test_expired_cookie_returns_401()`
  - `test_tampered_cookie_returns_401()`
  - `test_rolling_renewal_sets_new_cookie()`
- **Comando:** `cd backend && uv run pytest tests/test_session_middleware.py -v` (FALHA)
- **Checkpoint JP:** não

#### Task 11 — GREEN: session middleware + current_user dependency
- **Specialist:** per4biz-backend-python
- **Fase TDD:** GREEN · **Estimativa:** 12min
- **Files:**
  - `backend/app/middleware/__init__.py`
  - `backend/app/middleware/session.py`
  - `backend/app/deps.py` (dependency `current_user()`)
- **Detalhe:** Middleware lê cookie `__Host-session`, decodifica JWT, injeta `request.state.current_user`. Dependency `current_user()` retorna user ou levanta `HTTPException(401)`. Rolling renewal: se `iat > 6d`, emite novo cookie no response.
- **Comando:** `cd backend && uv run pytest tests/test_session_middleware.py -v`
- **Checkpoint JP:** não

---

### Track 4 — GDPR Trilogy (Tasks 12-13)

#### Task 12 — RED: /me endpoints tests
- **Specialist:** per4biz-qa-tdd
- **AC coberto:** AC-5 (revoke), AC-6 (external revoke)
- **Fase TDD:** RED · **Estimativa:** 10min
- **Files:**
  - `backend/tests/test_me_endpoints.py`
- **Detalhe:** Testes:
  - `test_get_me_returns_profile()`
  - `test_get_me_export_returns_json_dump_all_user_data()` (users + google_accounts ciphered indicator + consent_log + app_settings)
  - `test_delete_me_revokes_google_tokens()` (mock `oauth2.googleapis.com/revoke`)
  - `test_delete_me_cascades_delete_all_tables()` (users cascade → google_accounts + email_cache + drafts + voice_sessions + consent_log)
  - `test_delete_me_clears_cookie()` (`Set-Cookie: __Host-session=; Max-Age=0`)
- **Comando:** `cd backend && uv run pytest tests/test_me_endpoints.py -v` (FALHA)
- **Checkpoint JP:** não

#### Task 13 — GREEN: /me endpoints
- **Specialist:** per4biz-backend-python
- **Fase TDD:** GREEN · **Estimativa:** 15min
- **Files:**
  - `backend/app/routers/me.py` (GET `/me`, GET `/me/export`, DELETE `/me`)
  - `backend/app/main.py` — registar
- **Detalhe:** `GET /me` devolve perfil básico. `GET /me/export` devolve JSON dump (sem `refresh_token_encrypted` — apenas flag `has_token: true`). `DELETE /me` itera `google_accounts`, chama Google revoke para cada refresh_token (após decifrar), depois `supabase.delete()` com cascade, limpa cookie.
- **Comando:** `cd backend && uv run pytest tests/test_me_endpoints.py -v && uv run pytest --cov=app --cov-report=term`
- **Checkpoint JP:** 🔴 **sim (Checkpoint 2)** — backend completo; JP revê diff + testa endpoint `/health` e inspeciona schema aplicado

---

### Track 5 — Frontend (Tasks 14-17)

#### Task 14 — RED: welcome page tests
- **Specialist:** per4biz-qa-tdd + per4biz-frontend-pwa
- **AC coberto:** AC-1, AC-2
- **Fase TDD:** RED · **Estimativa:** 10min
- **Files:**
  - `frontend/tests/welcome.test.tsx`
  - `frontend/tests/e2e/login-flow.spec.ts` (Playwright, mock backend)
- **Detalhe:** Vitest+RTL:
  - `renders "Entrar com Google" button with Google "G" logo`
  - `clicking button navigates to /auth/google/start` (mocka `window.location`)
  - `shows error toast if URL has ?error=access_denied` (AC-2)
- Playwright:
  - `full happy login path with mocked backend returns to /inbox`
- **Comando:** `cd frontend && npm run test:run && npm run test:e2e` (FALHA)
- **Checkpoint JP:** não

#### Task 15 — GREEN: welcome page
- **Specialist:** per4biz-frontend-pwa + per4biz-ui-ux
- **Fase TDD:** GREEN · **Estimativa:** 15min
- **Files:**
  - `frontend/app/page.tsx` (substituir stub existente)
  - `frontend/components/ui/button.tsx` (shadcn Button via `npx shadcn add button` se não existe)
  - `frontend/components/google-g-logo.tsx` (SVG oficial inline do brand guidelines)
  - `frontend/lib/utils.ts` (cn utility) se não existe
- **Detalhe:** Welcome screen conforme SPEC §6: logo Per4Biz + tagline + CTA shadcn Button `primary lg 56px` com ícone Google G + texto "Entrar com Google". Copy PT-PT. Safe-area insets iOS. Link sutil "Política de privacidade" no rodapé → `/privacy`.
- **Comando:** `cd frontend && npm run test:run && npm run typecheck && npm run lint`
- **Checkpoint JP:** não

#### Task 16 — GREEN: loading screen pós-callback
- **Specialist:** per4biz-frontend-pwa + per4biz-ui-ux
- **AC coberto:** AC-1 (UX do loading)
- **Fase TDD:** GREEN · **Estimativa:** 8min
- **Files:**
  - `frontend/app/auth/loading/page.tsx`
- **Detalhe:** Fullscreen splash brand com spinner + texto "A preparar a sua caixa..." em PT-PT. Sem dismiss. Redireciona para `/inbox` após 2s ou quando middleware confirmar sessão.
- **Comando:** `cd frontend && npm run typecheck`
- **Checkpoint JP:** não

#### Task 17 — GREEN: settings/account + modal de revoke
- **Specialist:** per4biz-frontend-pwa + per4biz-ui-ux
- **AC coberto:** AC-5 (revoke manual)
- **Fase TDD:** GREEN · **Estimativa:** 18min
- **Files:**
  - `frontend/app/settings/account/page.tsx`
  - `frontend/components/ui/dialog.tsx` (shadcn Dialog)
  - `frontend/components/revoke-account-modal.tsx`
  - `frontend/tests/revoke-modal.test.tsx`
- **Detalhe:** Card com email + avatar + botão destructive "Desvincular e apagar conta". Modal confirmação dupla: input onde user tem de escrever "APAGAR" (disable Submit até match exato). POST `DELETE /me` no submit, redireciona para `/` com toast "Conta apagada com sucesso".
- **Comando:** `cd frontend && npm run test:run && npm run test:e2e`
- **Checkpoint JP:** 🔴 **sim (Checkpoint 3)** — frontend completo; JP abre `npm run dev` e revê visualmente 3 ecrãs + toma screenshot

---

### Track 6 — E2E (Tasks 18-19)

#### Task 18 — E2E: happy path completo
- **Specialist:** per4biz-qa-tdd + per4biz-frontend-pwa
- **AC coberto:** AC-1, AC-3, AC-4
- **Fase TDD:** GREEN (E2E) · **Estimativa:** 15min
- **Files:**
  - `frontend/tests/e2e/auth-happy-path.spec.ts`
  - `frontend/playwright.config.ts` (adicionar projeto mobile Safari iOS 16.4+ se não existe)
- **Detalhe:** Playwright simula consent Google via network interception (não bate em Google real). Fluxo: home → click "Entrar" → callback mocked → loading → inbox. Verifica cookie `__Host-session` existe. Reabre browser → inbox direto (AC-3).
- **Comando:** `cd frontend && npm run test:e2e`
- **Checkpoint JP:** não

#### Task 19 — E2E: cancel flow
- **Specialist:** per4biz-qa-tdd
- **AC coberto:** AC-2
- **Fase TDD:** GREEN (E2E) · **Estimativa:** 8min
- **Files:**
  - `frontend/tests/e2e/auth-cancel.spec.ts`
- **Detalhe:** Simula `?error=access_denied` na callback. Verifica redirect para `/` + toast "Login cancelado — tens de aceitar para usar o Per4Biz".
- **Comando:** `cd frontend && npm run test:e2e && cd ../backend && uv run pytest --cov=app` (coverage target 80%)
- **Checkpoint JP:** 🔴 **sim (Checkpoint 4)** — Sprint 1 done; JP revê coverage + todos os ACs + aprova merge/commit

---

## Checkpoints resumidos

| # | Quando | Quem revê | Critério de avanço |
|---|---|---|---|
| **0** | Antes de Task 1 | JP | "Aprovo o PLAN" |
| **1** | Após Task 6 | JP | Infra foundation verde, 3 services + 15 tests ✅ |
| **2** | Após Task 13 | JP | Backend E1 completo, cobertura ≥ 80%, migrations aplicadas |
| **3** | Após Task 17 | JP | Frontend completo, 3 ecrãs revistos visualmente, PT-PT ok |
| **4** | Após Task 19 | JP | Sprint 1 done, todos ACs cobertos, E2E verde → merge |

---

## Riscos locais e mitigações

| # | Risco | Impacto | Probab. | Mitigação |
|---|---|---|---|---|
| R-E1.1 | **iOS Safari PWA standalone** perde cookie `__Host-session` (modo instalado) | Alto | Média | Teste físico em Checkpoint 3; fallback documentado em ADR se falhar |
| R-E1.2 | **CASA Tier 2** atrasa produção pública | Baixo (V1 só testing mode) | Baixa | Submeter verificação no Sprint 0 Dia 1 — ver SPRINT-PLAN §8 R1 |
| R-E1.3 | **Google testing mode quota** (100 usuários, 100 tokens/dia) | Baixo para V1 (JP only) | Baixa | Monitorar via Google Cloud Console; upgrade para verified se beta alargar |
| R-E1.4 | **MCP Supabase** aponta para projeto errado (detectado 2026-04-15) | Médio (bloqueia integration tests) | Alta | Aplicar migrations manualmente via Dashboard SQL Editor (ver pré-req); reconfigurar MCP fora deste PLAN |
| R-E1.5 | **Refresh token Google** não devolvido em 2º consent (Google só dá na 1ª vez) | Médio | Média | Always include `prompt=consent access_type=offline` no URL de start |

---

## Cobertura de ACs (SPEC §7)

| AC | Descrição | Coberto em | Fase |
|---|---|---|---|
| **AC-1** | Primeiro login bem-sucedido | Task 7 (backend) + Task 14 + Task 18 (E2E) | RED+GREEN+E2E |
| **AC-2** | Login cancelado | Task 7 + Task 14 + Task 19 (E2E) | RED+GREEN+E2E |
| **AC-3** | Sessão persiste após reabrir app | Task 5, 10, 11, 18 | RED+GREEN+E2E |
| **AC-4** | Refresh automático de access token | Task 7 (via refresh flow em callback test) + futuro Sprint 2 ao chamar Gmail | RED+GREEN (parcial, completa em S2) |
| **AC-5** | Revogação manual pelo user | Task 12 + Task 17 | RED+GREEN |
| **AC-6** | Revogação externa (via myaccount.google.com) | Task 12 (`test_invalid_grant` em integration) | RED+GREEN |
| **AC-7** | Segurança CSRF no callback | Task 3 + Task 7 + Task 8 | RED+GREEN |
| **AC-8** | Tokens nunca em logs | Task 1 + Task 7 + Task 9 | RED+GREEN+REFACTOR |

---

## Estimativa total

**Tempo focado:** ~4h10min (250min) de specialist work puro.
**Com checkpoints JP:** +45-60min de review humana.
**Wall-clock realista:** **1-2 dias de trabalho** (conforme disponibilidade para checkpoints).

---

## Próximo passo

1. JP aplica migrations 0001-0004 no Supabase Dashboard (paralelo ao review do PLAN)
2. JP cria OAuth Client ID no Google Cloud Console (`http://localhost:8000/auth/google/callback` como redirect URI autorizado)
3. JP aprova este PLAN → **Checkpoint 0** ✅
4. Lançar per4biz-qa-tdd para Task 1 (RED crypto tests)

**Fim do PLAN.**
