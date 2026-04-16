# backend/ — Per4Biz Microserviço Python

FastAPI 0.115 + Pydantic v2 + Python 3.12 + uv (package manager).

## Estado

**Vazio.** Scaffold a criar no **Sprint 0 — Dia 2**.

## Scaffold esperado (Sprint 0)

```
backend/
├── app/
│   ├── main.py                     ← FastAPI app + middleware
│   ├── config.py                   ← Pydantic Settings (env vars)
│   ├── routers/
│   │   ├── auth.py                 ← /auth/google/*
│   │   ├── accounts.py             ← /accounts
│   │   ├── emails.py               ← /emails/*
│   │   ├── calendar.py             ← /calendar/* (V2)
│   │   ├── contacts.py             ← /contacts/* (V2)
│   │   ├── voice.py                ← /voice/process
│   │   └── webhooks.py             ← /webhooks/gmail-push
│   ├── integrations/
│   │   ├── google/                 ← OAuth flow, Gmail, Calendar, People
│   │   ├── groq.py                 ← STT + intent
│   │   ├── anthropic_client.py     ← Claude drafts
│   │   └── elevenlabs.py           ← TTS streaming
│   ├── services/
│   │   ├── email_service.py
│   │   ├── voice_service.py
│   │   └── account_service.py
│   ├── db/
│   │   ├── supabase_client.py      ← service_role client
│   │   └── queries/
│   ├── security/
│   │   ├── encryption.py           ← AES-256-GCM tokens
│   │   ├── jwt.py                  ← Supabase JWT validation
│   │   └── mtls.py                 ← shared secret BFF↔FastAPI
│   ├── workers/
│   │   └── sync_emails.py          ← arq worker
│   └── models/                     ← Pydantic schemas
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml                  ← uv
├── Dockerfile
├── fly.toml
└── .python-version                 ← 3.12
```

## Comandos (quando scaffold existir)

```bash
uv sync                                   # instalar deps
uv run uvicorn app.main:app --reload      # dev (porta 8000)
uv run pytest                              # tests
uv run pytest -k "test_name"               # test único
uv run pytest --cov=app                    # coverage
uv run ruff check .                        # lint
uv run ruff format .                       # format
uv run mypy app                            # types
```

## Deploy

```bash
fly deploy --region mad                   # Fly.io Madrid
```

## Referências

- Endpoints REST: [../02-ultraplan/ULTRAPLAN-tecnico.md §4.4](../02-ultraplan/ULTRAPLAN-tecnico.md)
- Pipeline voice agent: [../02-ultraplan/ULTRAPLAN-tecnico.md §5](../02-ultraplan/ULTRAPLAN-tecnico.md)
- Segurança (AES-GCM, mTLS, RLS): [../02-ultraplan/ULTRAPLAN-tecnico.md §6](../02-ultraplan/ULTRAPLAN-tecnico.md)
