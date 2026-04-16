# Testing Strategy — Per4Biz

**Estratégia de testes formal.** Aplicar em todas as user stories. Integra-se com o workflow Superpowers `test-driven-development` (RED-GREEN-REFACTOR).

---

## 1. Pirâmide de testes

```
                    ┌──────────────┐
                    │   E2E (10)   │         ← Playwright, fluxos críticos
                    └──────────────┘
                ┌────────────────────┐
                │ Integration (~40)  │        ← API endpoints reais c/ DB test
                └────────────────────┘
        ┌──────────────────────────────┐
        │     Unit tests (~200+)       │      ← Funções puras, mocks
        └──────────────────────────────┘
    ┌──────────────────────────────────────┐
    │  Manual Exploratory (todas sprints)  │  ← iPhone + Android reais
    └──────────────────────────────────────┘
```

### Quando executar

| Nível | Ferramenta | Cobertura alvo | Quando |
|---|---|---|---|
| **Unit** | Vitest (frontend) / pytest (backend) | ≥ 70% | A cada commit (pre-commit + CI) |
| **Integration** | Vitest + MSW / pytest + `httpx.AsyncClient` + Supabase local | Todos endpoints críticos | A cada PR |
| **E2E** | Playwright | 10 fluxos happy path | Antes de deploy para production |
| **Manual exploratório** | iPhone + Android reais | UX + voz + performance | Final de cada sprint |

---

## 2. Unit Tests — o que testar

### Backend Python

| Módulo | Funções críticas | Casos obrigatórios |
|---|---|---|
| `security/encryption.py` | `encrypt_token()`, `decrypt_token()`, `rotate_key()` | Cifra/decifra correto; token inválido → exceção; key rotation preserva dados; nonce único por cifra |
| `security/jwt.py` | `validate_supabase_jwt()`, `extract_user_id()` | JWT válido; expirado → 401; signature inválida → 401; aud/iss incorreto → 401 |
| `integrations/google_oauth.py` | `build_auth_url()`, `exchange_code()`, `refresh_access_token()` | state JWT válido; code expirado → erro; refresh success; `invalid_grant` → limpa DB |
| `integrations/gmail.py` | `list_messages()`, `parse_mime()`, `send_message()` | MIME HTML → texto limpo; corpo multipart; headers em falta; attachments meta extraído |
| `integrations/groq_client.py` | `transcribe()`, `classify_intent()` | Audio vazio → erro; timeout → raise; retry em 5xx |
| `integrations/anthropic_client.py` | `generate_draft()` | Prompt PT-PT correto; tom configurado respeitado; streaming chunks |
| `services/email_service.py` | `get_inbox()`, `mark_read()`, `send_draft()` | RLS respeitado (user_id check); cache hit vs miss; draft não aprovado → rejeita envio |
| `services/voice_service.py` | `process_voice_session()` | Pipeline completo; fallback cascade; session id propagado |
| `workers/sync_emails.py` | `sync_account()` | Gmail `watch()` renew; Pub/Sub message handling; dedup |

### Frontend TypeScript

| Componente / hook | Testes obrigatórios |
|---|---|
| `VoiceButton` | Estados idle/listening/processing/done; haptic disparado; aria-label correto |
| `EmailListItem` | Render unread vs read; swipe actions; barra cor da conta |
| `TranscriptText` | Palavras confirmed (preto) vs hypothesis (cinza); fade 120ms |
| `useVoiceRecorder` hook | Permission denied → throw; start/stop; cleanup MediaRecorder |
| `useEmailsQuery` hook | Cache React Query; refetch on account switch; error states |
| `lib/supabase/client.ts` | Session persistence; refresh silencioso; signOut limpa |
| `utils/format.ts` | `formatDate` PT-PT; `sanitizeEmailBody` remove scripts |

---

## 3. Integration Tests — cenários por endpoint

### Setup

- **Backend:** `pytest-asyncio` + `httpx.AsyncClient` com app FastAPI; Supabase local via `supabase start`; seed mínimo em `conftest.py`.
- **Frontend:** Vitest + MSW (Mock Service Worker) para interceptar chamadas ao BFF; Supabase mock via `@supabase/ssr` test helpers.

### Endpoints críticos a cobrir

| Endpoint | Cenários mínimos |
|---|---|
| `GET /auth/google/login` | Redireciona com state JWT válido; erro se `ENCRYPTION_KEY` ausente |
| `GET /auth/google/callback` | code válido → 302 + cria DB; state inválido → 400; code expirado → 400 |
| `DELETE /me` | Apaga cascata; revoga Google; retorna 204; 2ª chamada → 404 |
| `GET /accounts` | Lista só contas do user (RLS); cross-tenant → 403 |
| `GET /emails?account_id=X` | Lista cached; respeita limit/cursor; account não-minha → 403 |
| `GET /emails/{id}` | Cache hit devolve; cache miss → fetch Gmail; body sanitizado |
| `POST /emails/draft` | Claude chamado; body_text devolvido; rate limit 429 aos > 200/dia |
| `POST /emails/send` | Só envia se `draft.status='approved'`; 400 se não; Gmail 5xx → retry |
| `POST /voice/process` | STT → intent → LLM → TTS; latency tracking; fallback cascade |
| `POST /webhooks/gmail-push` | Pub/Sub auth válido; update cache; invalid token → 401 |

---

## 4. E2E Tests — 10 fluxos críticos (Playwright)

| ID | Fluxo | Passos | Critério de sucesso |
|---|---|---|---|
| **E2E-01** | Onboarding completo | 1. Abrir PWA → 2. "Entrar com Google" → 3. Autorizar scopes (test account) → 4. Aterrar em `/inbox` | Username visível no header em < 8s |
| **E2E-02** | Ler email em voz | 1. Abrir email → 2. Tap "Ouvir" → 3. Esperar TTS | Áudio começa em < 1.5s; sem HTML falado |
| **E2E-03** | Responder por voz end-to-end | 1. Abrir email → 2. "Responder por voz" → 3. Ditar 10s → 4. Aprovar draft → 5. Enviar | Email chega ao destinatário de teste; toast "Enviado" |
| **E2E-04** | Compose novo por voz | 1. FAB voice → 2. "manda email ao João a dizer sim" → 3. Confirmar | Draft criado e enviado; visível em Gmail Sent |
| **E2E-05** | Switch de conta (V1.x) | 1. Swipe down no header → 2. Selecionar 2ª conta → 3. Ver inbox | Inbox muda em < 500ms; emails da 2ª conta visíveis |
| **E2E-06** | Revogar conta | 1. Settings → 2. Desvincular → 3. Confirmar "APAGAR" | Conta desaparece; Gmail em myaccount.google.com mostra revogado |
| **E2E-07** | PWA install + standalone | 1. Abrir em Safari iOS → 2. Adicionar à tela inicial → 3. Abrir standalone | App abre sem browser chrome; ícone maskable; sessão persiste |
| **E2E-08** | Offline: ler cache + outbox | 1. Abrir app → 2. Desligar rede → 3. Ver inbox cacheada → 4. Tentar enviar draft | Inbox visível; draft na outbox; ao religar → draft enviado |
| **E2E-09** | Criar evento por voz (V2) | 1. FAB voice → 2. "marca reunião amanhã às 15h com Ana" → 3. Confirmar | Evento no Google Calendar amanhã 15:00 |
| **E2E-10** | Recuperação de token expirado | 1. Login → 2. Esperar 1h+ → 3. Listar emails | Refresh transparente; sem re-login; emails carregam |

### Ambiente de E2E

- **Google test accounts:** 2 contas dedicadas com OAuth consent em modo testing.
- **Data seed:** script que popula inboxes de teste com 20 emails variados.
- **Playwright config:** `playwright.config.ts` com `viewport: iPhone 15 Pro` + device emulation para Android Pixel 7.
- **Run:** headless em CI; `--headed` localmente para debug.

---

## 5. Manual exploratory — checklist por sprint

No final de cada sprint, o JP (ou QA agent) percorre o checklist em **iPhone real + Android real**:

```
☐ App instala via "Adicionar à tela inicial" (iOS + Android)
☐ Ícone e splash screen corretos, cor de marca
☐ Safe-areas respeitadas (notch, home indicator)
☐ Portrait only, orientation lock funciona
☐ Tap targets ≥ 48px, sem cliques falhados
☐ Swipe gestures na inbox funcionam suavemente
☐ Pull-to-refresh com haptic
☐ VoiceButton: idle → listening → processing → done sem glitches visuais
☐ Transcrição em tempo real aparece fluidamente
☐ TTS em PT-PT soa natural (não robótico)
☐ Dark mode funciona, transição suave
☐ prefers-reduced-motion respeitado
☐ Accessibility: VoiceOver/TalkBack navega
☐ Offline: shell carrega, banner mostra
☐ Push notification chega (iOS 16.4+ standalone)
☐ Performance: scroll 60fps, sem jank
☐ Rede lenta (3G throttling DevTools): app ainda usável
☐ Reboot do device: sessão persiste
```

---

## 6. Configuração CI (GitHub Actions)

### `.github/workflows/backend.yml`

```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - uses: supabase/setup-cli@v1
      - run: supabase start
      - run: cd backend && uv sync
      - run: cd backend && uv run ruff check .
      - run: cd backend && uv run mypy app
      - run: cd backend && uv run pytest --cov=app --cov-fail-under=70
      - run: supabase stop
```

### `.github/workflows/frontend.yml`

```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run typecheck
      - run: cd frontend && npm run test:run -- --coverage
      - if: github.ref == 'refs/heads/main'
        run: cd frontend && npx playwright install --with-deps
      - if: github.ref == 'refs/heads/main'
        run: cd frontend && npm run test:e2e
```

### Gates obrigatórios no PR

- ✅ Lint clean (ruff backend, eslint frontend)
- ✅ Types clean (mypy backend, tsc frontend)
- ✅ Unit tests pass com coverage ≥ 70%
- ✅ Integration tests pass
- ⚠️ E2E só corre em `main` (por tempo + custo); em PR correr só E2E smoke (3 testes).

---

## 7. TDD workflow (Superpowers-aligned)

Para cada task em `plans/<feature>/PLAN.md`:

```
┌─────────────────────────────────────────────────────┐
│  1. RED — Escrever teste que falha                  │
│     - Teste específico do AC correspondente         │
│     - Correr: deve FALHAR ("assertion error")       │
│     - Commit: "test(scope): failing test for X"     │
├─────────────────────────────────────────────────────┤
│  2. GREEN — Escrever código MÍNIMO para passar      │
│     - Só o suficiente; nada mais                    │
│     - Correr: deve PASSAR                           │
│     - Commit: "feat(scope): implement X"            │
├─────────────────────────────────────────────────────┤
│  3. REFACTOR — Melhorar sem quebrar                 │
│     - Extrair funções, nomear melhor                │
│     - Testes continuam verdes                       │
│     - Commit: "refactor(scope): clean up X"         │
└─────────────────────────────────────────────────────┘
```

**Regra Superpowers:** não saltar o passo RED. Código escrito antes do teste que falha deve ser apagado.

---

## 8. Mapeamento AC → teste

Cada AC em [ACCEPTANCE-CRITERIA.md](ACCEPTANCE-CRITERIA.md) tem de ter **pelo menos 1 teste** que o verifica. Padrão de nomeação:

```python
# backend/tests/unit/test_email_service.py
def test_list_inbox_respects_rls():  # cobre AC-E2.US1-3
    """RLS blocks cross-tenant email access."""
    ...

def test_list_inbox_pagination_cursor():  # cobre AC-E2.US1-2
    ...
```

```typescript
// frontend/tests/unit/VoiceButton.test.tsx
describe('VoiceButton', () => {
  test('tap triggers listening state — AC-E4.US2-1', () => { ... });
  test('permission denied shows fallback modal — AC-E4.US2-3', () => { ... });
});
```

Em PR description:

```
## ACs cobertos
- AC-E2.US1-1 ✅ (test_list_inbox_basic)
- AC-E2.US1-2 ✅ (test_list_inbox_pagination_cursor)
- AC-E2.US1-3 ✅ (test_list_inbox_respects_rls)
```

---

## 9. Test data fixtures

### Backend (`conftest.py`)

```python
@pytest.fixture
async def test_user(supabase_client):
    user = await supabase_client.auth.admin.create_user({
        "email": f"test+{uuid4()}@per4biz.app",
        "email_confirm": True,
    })
    yield user
    await supabase_client.auth.admin.delete_user(user.id)

@pytest.fixture
async def test_google_account(test_user, db):
    account = await create_test_account(
        user_id=test_user.id,
        google_email="test@gmail.com",
        refresh_token_plaintext="mock_refresh_token",
    )
    yield account
    await db.delete("google_accounts", id=account.id)
```

### Frontend (MSW handlers)

```typescript
// tests/mocks/handlers.ts
export const handlers = [
  http.get('/api/emails', () => HttpResponse.json(mockEmails)),
  http.post('/api/voice/process', () => HttpResponse.json(mockVoiceResponse)),
];
```

---

## 10. Performance & load testing (opcional V1, obrigatório V1.x+)

| Métrica | Alvo | Ferramenta |
|---|---|---|
| p95 latência voz end-to-end | < 4s | k6 script simulando 10 sessions simultâneas |
| p95 listagem inbox | < 1s | k6 |
| FCP PWA | < 1.5s em 4G | Lighthouse CI |
| Bundle size frontend | < 250 KB gzipped | `@next/bundle-analyzer` |

---

## 11. Regression tracking

Manter `tests/regression/` com testes que reproduzem bugs corrigidos. Cada bug → 1 teste permanente. Nome:

```
test_regression_GH42_token_refresh_race_condition()
```
