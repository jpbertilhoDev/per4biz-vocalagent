"""
Testes RED para `app.middleware.session` + `app.deps.current_user`
(Sprint 1 · E1 · Task 10).

Cobrem o SPEC §5.3 e §4.2 (edge cases) — o middleware lê o cookie
`__Host-session`, valida via `decode_session`, injecta o payload em
`request.state.current_user` e aplica rolling renewal (Set-Cookie na
response quando `maybe_renew` devolve token novo). A dependency
`current_user` levanta 401 quando não há sessão válida.

Mapeiam aos ACs:
    - AC-3: sessão persiste 7 dias com rolling renewal perto da expiração.
    - AC-6: cookies inválidos/corrompidos forçam re-login (401).

Enquanto `app/middleware/session.py` e `app/deps.py` não existirem, a
colecção falha com `ModuleNotFoundError` — RED autêntica. Após Task 11
(GREEN), os 5 testes passam sem alterar o test file.

**Nota sobre `__Host-` em TestClient:**
O prefixo `__Host-` exige `Secure` + `Path=/` + sem `Domain`. Browsers
recusam sem HTTPS, mas `starlette.testclient.TestClient` (httpx) não
reforça essa regra — o cookie chega ao servidor normalmente. Aqui
setamos via `client.cookies.set(name, token)` sem flags extra.
"""
from __future__ import annotations

import time
from uuid import UUID

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from jose import jwt

from app.config import get_settings
from app.services.session_jwt import issue_session

# --- Imports dos módulos ainda não existentes (Task 11 — GREEN) ------------
# Import top-level garante que a colecção inteira falha com ModuleNotFoundError
# até Task 11 criar `app/middleware/session.py` e `app/deps.py`.
from app.deps import current_user  # noqa: F401 — usado na fixture protected_app

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
EMAIL = "test@per4biz.local"
COOKIE_NAME = "__Host-session"


# ---------------------------------------------------------------------------
# Fixture: adiciona rota `/__test/protected` ao app para esta suite.
# ---------------------------------------------------------------------------
@pytest.fixture
def protected_client(client: TestClient) -> TestClient:
    """Adiciona rota `/__test/protected` protegida por `current_user`.

    Scope: function — a rota é registada idempotentemente (verifica path
    antes de adicionar) para evitar `Duplicate path` em re-runs na mesma
    sessão do pytest. O middleware é registado pelo `create_app()` em
    `app.main`; esta fixture apenas expõe uma rota que exerce a
    dependency `current_user`.
    """
    from app.main import app

    if not any(getattr(r, "path", None) == "/__test/protected" for r in app.routes):

        @app.get("/__test/protected")
        def _protected(user: dict = Depends(current_user)) -> dict[str, dict]:  # type: ignore[misc]
            return {"user": user}

    return client


# ---------------------------------------------------------------------------
# 1. Cookie ausente → 401 (AC-6)
# ---------------------------------------------------------------------------
def test_missing_cookie_returns_401_on_protected_route(
    protected_client: TestClient,
) -> None:
    """SPEC §4.2 · AC-6: request sem cookie `__Host-session` é rejeitado.

    A dependency `current_user` levanta `HTTPException(401)` quando
    `request.state.current_user` é `None` (middleware não encontrou
    cookie válido).
    """
    response = protected_client.get("/__test/protected")

    assert response.status_code == 401, (
        f"esperado 401 sem cookie, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )


# ---------------------------------------------------------------------------
# 2. Cookie válido → injecta current_user (AC-3)
# ---------------------------------------------------------------------------
def test_valid_cookie_injects_current_user(protected_client: TestClient) -> None:
    """SPEC §5.3 · AC-3: cookie válido popula `request.state.current_user`.

    O middleware decodifica o JWT e injecta dict `{sub, email, iat, exp}`
    em `request.state.current_user`. A dependency devolve esse dict ao
    handler, que o serializa em JSON.
    """
    token = issue_session(USER_ID, EMAIL)

    # `TestClient` não reforça o prefixo `__Host-` (httpx-level); o cookie
    # chega ao servidor como qualquer outro. Ver docstring do módulo.
    protected_client.cookies.set(COOKIE_NAME, token)
    response = protected_client.get("/__test/protected")
    protected_client.cookies.clear()  # limpa entre testes para evitar leak

    assert response.status_code == 200, (
        f"esperado 200 com cookie válido, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )
    body = response.json()
    assert body["user"]["sub"] == str(USER_ID), (
        f"sub esperado={USER_ID!s}, recebido={body['user'].get('sub')!r}"
    )
    assert body["user"]["email"] == EMAIL, (
        f"email esperado={EMAIL!r}, recebido={body['user'].get('email')!r}"
    )


# ---------------------------------------------------------------------------
# 3. Cookie expirado → 401 (AC-6)
# ---------------------------------------------------------------------------
def test_expired_cookie_returns_401(protected_client: TestClient) -> None:
    """SPEC §4.2 · AC-6: token com `exp` no passado → middleware rejeita.

    `decode_session` propaga `ExpiredSignatureError`; middleware captura
    e deixa `request.state.current_user = None`, resultando em 401 via
    dependency.
    """
    settings = get_settings()
    expired_token = jwt.encode(
        {"sub": str(USER_ID), "email": EMAIL, "iat": 1, "exp": 2},
        settings.INTERNAL_API_SHARED_SECRET,
        algorithm="HS256",
    )

    protected_client.cookies.set(COOKIE_NAME, expired_token)
    response = protected_client.get("/__test/protected")
    protected_client.cookies.clear()

    assert response.status_code == 401, (
        f"esperado 401 com cookie expirado, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )


# ---------------------------------------------------------------------------
# 4. Cookie adulterado → 401 (AC-6)
# ---------------------------------------------------------------------------
def test_tampered_cookie_returns_401(protected_client: TestClient) -> None:
    """SPEC §5.3 · AC-6: token com payload adulterado → 401.

    Alterar 1 char do segmento payload quebra a assinatura HS256.
    `decode_session` propaga `JWTError`, middleware neutraliza,
    dependency devolve 401.
    """
    token = issue_session(USER_ID, EMAIL)
    header, payload, signature = token.split(".")
    # Flip 1 char do meio do payload base64 (garante mudança real)
    mid = len(payload) // 2
    tampered_char = "A" if payload[mid] != "A" else "B"
    tampered_payload = payload[:mid] + tampered_char + payload[mid + 1 :]
    tampered_token = f"{header}.{tampered_payload}.{signature}"
    assert tampered_token != token, "tampering não alterou o token"

    protected_client.cookies.set(COOKIE_NAME, tampered_token)
    response = protected_client.get("/__test/protected")
    protected_client.cookies.clear()

    assert response.status_code == 401, (
        f"esperado 401 com cookie adulterado, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )


# ---------------------------------------------------------------------------
# 5. Rolling renewal → Set-Cookie com token novo (AC-3)
# ---------------------------------------------------------------------------
def test_rolling_renewal_sets_new_cookie(protected_client: TestClient) -> None:
    """SPEC §5.3 · AC-3: token com <1d restante é renovado na response.

    Fabricamos um token com 1h de vida restante (iat = now - 7d + 1h).
    O middleware deve:
        1. Aceitar o request (ainda válido) → 200.
        2. Chamar `maybe_renew`, que devolve token novo.
        3. Anexar `Set-Cookie: __Host-session=<novo>` à response.
    """
    settings = get_settings()
    now = int(time.time())
    iat = now - (7 * 86400) + 3600  # 1h restante
    old_token = jwt.encode(
        {"sub": str(USER_ID), "email": EMAIL, "iat": iat, "exp": iat + 7 * 86400},
        settings.INTERNAL_API_SHARED_SECRET,
        algorithm="HS256",
    )

    protected_client.cookies.set(COOKIE_NAME, old_token)
    response = protected_client.get("/__test/protected")
    protected_client.cookies.clear()

    assert response.status_code == 200, (
        f"esperado 200 com cookie quase-expirado, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )
    set_cookie = response.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie, (
        f"esperado Set-Cookie com `{COOKIE_NAME}`, recebido: {set_cookie!r}"
    )
    # Extrai o valor do novo token do header Set-Cookie
    # Formato típico: `__Host-session=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/`
    new_token_part = set_cookie.split(f"{COOKIE_NAME}=", 1)[1].split(";", 1)[0]
    assert new_token_part != old_token, (
        "Set-Cookie contém o mesmo token — renewal não ocorreu"
    )
