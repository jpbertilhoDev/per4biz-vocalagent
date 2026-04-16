"""
Testes RED para os endpoints `/emails` (Sprint 1.x · E2 · Task 3).

Router alvo:
    `app.routers.emails` (a criar na Task 4) — expõe:

        - `GET /emails/list?page_token=...&limit=50` → lista paginada
          `{"emails": [...], "next_page_token": "..."}` (AC-2.1 · RF-2.6).
        - `GET /emails/{message_id}` → email completo com `body_text`
          sanitizado (AC-2.2 · SPEC §6).

ACs cobertos:
    - AC-2.1 (lista paginada com max 50 emails · SPEC §6)
    - AC-2.2 (body_text HTML strippado · SPEC §6)
    - AC-2.7 (invalid_grant → 401 + cleanup de `google_accounts` +
      cookie `__Host-session` limpo · SPEC §6)

**Simplificação V1:** sem teste de rate limit (adiado para Sprint 2
DevOps quando Upstash Redis estiver configurado).

Enquanto `app/routers/emails.py` não existir e não estiver registado em
`app/main.py`, estes testes falham com `404 Not Found` em todas as rotas
(RED autêntica — FastAPI não conhece `/emails/*`). Após GREEN (Task 4),
os 6 testes passam sem alterar este ficheiro.

Flags para o specialist (Task 4):
    - Criar `app/routers/emails.py` com `router = APIRouter(
      prefix="/emails", tags=["emails"])` e depender de `current_user`.
    - Registar em `app/main.py` via `app.include_router(emails.router)`.
    - `GET /emails/list` chama `gmail.list_messages(user["sub"],
      page_token=..., limit=...)` e devolve o dict raw (Pydantic response
      model opcional — este teste só verifica shape JSON).
    - `GET /emails/{message_id}` chama `gmail.get_message(user["sub"],
      message_id)` e devolve o dict raw.
    - **Ordem crítica no handler de `invalid_grant`** (AC-2.7):
        1. Capturar `google.auth.exceptions.RefreshError` (pode vir raw
           do `_get_valid_credentials` ou propagada pelo Gmail API call).
        2. `sb.table("google_accounts").delete().eq("user_id",
           user["sub"]).execute()` — apaga tokens revogados.
        3. Construir `JSONResponse(status_code=401, ...)` com
           `response.delete_cookie(SESSION_COOKIE)` ou `set_cookie(...,
           max_age=0)` para invalidar a sessão no browser.
        4. **Não** fazer revoke adicional no Google (token já foi revogado
           pelo próprio user em myaccount.google.com).
    - Mocks apontam para `app.services.gmail.list_messages` /
      `app.services.gmail.get_message` — isolamento do `googleapiclient`.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from google.auth.exceptions import RefreshError
from pytest_mock import MockerFixture

from app.services.session_jwt import issue_session

# ---------------------------------------------------------------------------
# Constantes partilhadas
# ---------------------------------------------------------------------------

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
USER_ID_STR = str(USER_ID)
EMAIL = "test@per4biz.local"
COOKIE_NAME = "__Host-session"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_cookies() -> dict[str, str]:
    """Cookie de sessão válido para testes autenticados (SPEC §5.3).

    Emite um session JWT HS256 com o `USER_ID`/`EMAIL` canónicos do
    conftest. O `SessionMiddleware` injecta `{sub, email}` em
    `request.state.current_user`, permitindo que os endpoints `/emails/*`
    resolvam a identidade sem consultar Supabase Auth.
    """
    token = issue_session(USER_ID, EMAIL)
    return {COOKIE_NAME: token}


def _build_supabase_delete_mock() -> MagicMock:
    """Mock encadeável `client.table(t).delete().eq(k, v).execute()`.

    Usado apenas pelo teste AC-2.7 para verificar que o handler faz
    cleanup de `google_accounts` antes de devolver 401.
    """
    client = MagicMock(name="supabase_client")
    table_mock = MagicMock(name="supabase_table_google_accounts")
    client.table.return_value = table_mock
    table_mock.delete.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    return client


def _sample_email_metadata(idx: int) -> dict[str, Any]:
    """Gera 1 item no shape devolvido por `gmail.list_messages` (RF-2.6)."""
    return {
        "id": f"m{idx}",
        "from_name": f"Sender {idx}",
        "from_email": f"s{idx}@example.com",
        "subject": f"Subject {idx}",
        "snippet": f"Preview {idx}",
        "received_at": "2026-04-15T12:00:00+00:00",
        "is_unread": idx == 1,
    }


# ---------------------------------------------------------------------------
# 1. GET /emails/list — requer cookie de sessão (SessionMiddleware)
# ---------------------------------------------------------------------------


def test_list_requires_auth(client) -> None:  # type: ignore[no-untyped-def]
    """Sem cookie `__Host-session` a rota devolve 401 (SPEC §5.3 · AC-6).

    O `SessionMiddleware` deixa `request.state.current_user = None` quando
    o cookie está ausente; a dep `current_user` converte isso em
    `HTTPException(401, "Authentication required")`.
    """
    response = client.get("/emails/list")

    assert response.status_code == 401, (
        f"esperado 401 sem cookie, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )


# ---------------------------------------------------------------------------
# 2. GET /emails/list — happy path (AC-2.1)
# ---------------------------------------------------------------------------


def test_list_returns_emails_happy_path(
    client, mocker: MockerFixture, auth_cookies: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """AC-2.1 (SPEC §6 · listar 50 emails recentes).

    Mocka `app.services.gmail.list_messages` para devolver 2 items fake;
    verifica que o endpoint propaga o shape JSON sem alterações e chama
    o service com `user["sub"]` + `page_token=None` + `limit=50` (defaults).
    """
    fake_result = {
        "emails": [_sample_email_metadata(1), _sample_email_metadata(2)],
        "next_page_token": "tok",
    }
    mock_list = mocker.patch(
        "app.services.gmail.list_messages",
        return_value=fake_result,
    )

    response = client.get("/emails/list", cookies=auth_cookies)

    assert response.status_code == 200, (
        f"esperado 200, recebido {response.status_code} (body: {response.text[:200]})"
    )
    body = response.json()
    assert "emails" in body, f"resposta sem key `emails`: {body}"
    assert len(body["emails"]) == 2, f"esperava 2 emails, recebeu {len(body['emails'])}"
    assert body.get("next_page_token") == "tok", (
        f"next_page_token ausente ou errado: {body}"
    )

    # Cada item deve preservar as keys do service (RF-2.6)
    for item in body["emails"]:
        for key in (
            "id",
            "from_name",
            "from_email",
            "subject",
            "snippet",
            "received_at",
            "is_unread",
        ):
            assert key in item, f"email item sem key `{key}`: {item}"

    # Service chamado com user_id canónico + defaults
    mock_list.assert_called_once_with(
        USER_ID_STR, page_token=None, limit=50
    )


# ---------------------------------------------------------------------------
# 3. GET /emails/list — paginação com page_token + limit (AC-2.1)
# ---------------------------------------------------------------------------


def test_list_paginates_with_page_token(
    client, mocker: MockerFixture, auth_cookies: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """AC-2.1 pagination — query params `page_token` e `limit` são
    propagados 1:1 para `gmail.list_messages`.
    """
    fake_result = {
        "emails": [_sample_email_metadata(1)],
        "next_page_token": None,
    }
    mock_list = mocker.patch(
        "app.services.gmail.list_messages",
        return_value=fake_result,
    )

    response = client.get(
        "/emails/list?page_token=abc&limit=20",
        cookies=auth_cookies,
    )

    assert response.status_code == 200, (
        f"esperado 200, recebido {response.status_code} (body: {response.text[:200]})"
    )
    mock_list.assert_called_once_with(
        USER_ID_STR, page_token="abc", limit=20
    )


# ---------------------------------------------------------------------------
# 4. GET /emails/{message_id} — requer cookie de sessão
# ---------------------------------------------------------------------------


def test_get_message_requires_auth(client) -> None:  # type: ignore[no-untyped-def]
    """Sem cookie, `GET /emails/{message_id}` devolve 401 (AC-6)."""
    response = client.get("/emails/somemessageid")

    assert response.status_code == 401, (
        f"esperado 401 sem cookie, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )


# ---------------------------------------------------------------------------
# 5. GET /emails/{message_id} — devolve body_text sanitizado (AC-2.2)
# ---------------------------------------------------------------------------


def test_get_message_returns_body_text(
    client, mocker: MockerFixture, auth_cookies: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """AC-2.2 (SPEC §6 · abrir email com body HTML strippado).

    O endpoint devolve o dict raw do service, incluindo `body_text`
    legível (o `gmail.get_message` já aplica `_html_to_text`). Este teste
    isola o router do service — só verifica propagação do shape.
    """
    fake_email = {
        "id": "m1",
        "from_email": "x@y.z",
        "from_name": "X",
        "subject": "S",
        "snippet": "Preview",
        "body_text": "Olá",
        "to_emails": [],
        "cc_emails": [],
        "received_at": "2026-04-15T12:00:00+00:00",
        "is_unread": False,
    }
    mock_get = mocker.patch(
        "app.services.gmail.get_message",
        return_value=fake_email,
    )

    response = client.get("/emails/m1", cookies=auth_cookies)

    assert response.status_code == 200, (
        f"esperado 200, recebido {response.status_code} (body: {response.text[:200]})"
    )
    body = response.json()
    assert body.get("body_text") == "Olá", (
        f"body_text ausente ou errado: {body}"
    )
    # Shape mínimo propagado
    for key in ("id", "from_email", "subject", "received_at", "is_unread"):
        assert key in body, f"resposta sem key `{key}`: {body}"

    mock_get.assert_called_once_with(USER_ID_STR, "m1")


# ---------------------------------------------------------------------------
# 6. AC-2.7: invalid_grant → 401 + limpa cookie + apaga google_accounts
# ---------------------------------------------------------------------------


def test_invalid_grant_returns_401_and_clears_cookie(
    client, mocker: MockerFixture, auth_cookies: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """AC-2.7 (SPEC §6 · refresh_token revogado externamente).

    Cenário: user revogou acesso em myaccount.google.com. Próxima chamada
    a `/emails/list` → `gmail.list_messages` levanta `RefreshError
    ("invalid_grant")`. O router deve:

        1. Apagar `google_accounts` do user (cleanup de tokens mortos).
        2. Devolver 401.
        3. Invalidar o cookie `__Host-session` (Max-Age=0 ou expires=1970)
           para que o browser force re-login no próximo request.
    """
    mocker.patch(
        "app.services.gmail.list_messages",
        side_effect=RefreshError("invalid_grant"),
    )
    supabase_mock = _build_supabase_delete_mock()
    mock_supabase = mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=supabase_mock,
    )

    response = client.get("/emails/list", cookies=auth_cookies)

    assert response.status_code == 401, (
        f"esperado 401 em invalid_grant, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )

    # Cookie invalidado — tem de aparecer Set-Cookie __Host-session com Max-Age=0
    set_cookie = response.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie, (
        f"Set-Cookie não contém `{COOKIE_NAME}`: {set_cookie!r}"
    )
    lower = set_cookie.lower()
    expired = ("max-age=0" in lower) or ("expires=" in lower and "1970" in lower)
    assert expired, (
        f"Set-Cookie não invalida a sessão (Max-Age=0 ou expires=1970 em falta): "
        f"{set_cookie!r}"
    )

    # Cleanup em google_accounts foi disparado
    assert mock_supabase.called, (
        "`get_supabase_admin` não foi chamado — cleanup de google_accounts em falta"
    )
    # Aceita qualquer ordem de chamadas; basta que tenha pedido a tabela correcta.
    mock_supabase.return_value.table.assert_any_call("google_accounts")
