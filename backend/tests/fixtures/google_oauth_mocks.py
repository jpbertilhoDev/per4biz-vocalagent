"""
Fixtures partilhadas de mock Google OAuth (Sprint 1 · E1 · Task 7).

Constantes usadas em `tests/test_auth_endpoints.py` para patchar
`app.services.google_oauth.exchange_code_for_tokens` e
`app.services.google_oauth.fetch_userinfo`.

Mapeia ao SPEC §4.1 (happy path) e §5.1 (tokens cifrados AES-256-GCM).
Nenhum destes valores é real — são strings sintéticas que não podem
coincidir com quaisquer tokens genuínos para garantir que os asserts
de redacção em logs (AC-8) validam o caminho correcto.
"""
from __future__ import annotations

from typing import Any

# Tokens fictícios devolvidos por `exchange_code_for_tokens`.
FAKE_TOKENS: dict[str, Any] = {
    "access_token": "ya29.fake_access",
    "refresh_token": "1//fake_refresh",
    "id_token": "fake.id.token",
    "expires_in": 3600,
    "token_type": "Bearer",
    "scope": (
        "openid email profile "
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/gmail.modify"
    ),
}

# Userinfo cujo email coincide com o `ALLOWED_USER_EMAIL` do conftest
# (ver `backend/tests/conftest.py` → `test@per4biz.local`).
FAKE_USERINFO_MATCH: dict[str, Any] = {
    "sub": "123456789012345678901",
    "email": "test@per4biz.local",
    "email_verified": True,
    "name": "Test User",
    "picture": "https://lh3.googleusercontent.com/a/fake=s96-c",
    "locale": "pt-PT",
}

# Userinfo de um atacante — email diferente do `ALLOWED_USER_EMAIL`,
# deve disparar 403 no callback e impedir qualquer escrita em Supabase.
FAKE_USERINFO_MISMATCH: dict[str, Any] = {
    "sub": "999999999999999999999",
    "email": "attacker@evil.com",
    "email_verified": True,
    "name": "Attacker",
    "picture": "https://lh3.googleusercontent.com/a/evil=s96-c",
    "locale": "en",
}
