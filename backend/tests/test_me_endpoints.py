"""
Testes RED para os endpoints `/me` (Sprint 1 · E1 · Task 12+13).

Cobrem a **GDPR trilogy** exigida pela `06-addendum/PRIVACY-POLICY-PT.md §11`:

    - `GET    /me`          → perfil básico do user logado (sem PII sensível)
    - `GET    /me/export`   → JSON dump portável (GDPR Art. 20 portability)
    - `DELETE /me`          → revoga tokens Google + cascade delete + limpa cookie

ACs alvo:
    - AC-5 (revoke manual de tokens Google — SPEC §5.5 / §3 RF-1.4)
    - AC-6 (cookie limpo após DELETE força re-login)
    - Cascade delete seguro — migration 0001/0004 declaram
      `ON DELETE CASCADE` nas FKs filhas (`google_accounts`, `email_cache`,
      `draft_responses`, `voice_sessions`, `consent_log`).

Enquanto `app/routers/me.py` não existir, a colecção falha com
`ModuleNotFoundError` — RED autêntica. Após Task 13 (GREEN), os 5 testes
passam sem alterar este ficheiro.

Flags para o specialist (Task 13):
    - Criar `app/routers/me.py` com `router = APIRouter(tags=["me"])`
    - Registar em `app/main.py` via `app.include_router(me_router.router)`
    - Depender de `current_user` para as 3 rotas (401 se sem cookie)
    - Criar helper `app.services.google_oauth.revoke_token(refresh_token: str) -> None`
      que faça `POST https://oauth2.googleapis.com/revoke?token=<rt>` e
      loga apenas `status_code` (nunca o token).
    - Ordem de operações no `DELETE /me`:
        1. SELECT `google_accounts` para obter `refresh_token_encrypted`
        2. Decrypt + chamar `revoke_token(plaintext)` (best-effort: log warning
           se 4xx/5xx, mas prossegue — AC-6 external revocation já tratada)
        3. DELETE explícito em `users` (cascade apanha filhas) OU delete
           explícito por tabela (defence in depth). Ambas as estratégias
           são aceites pelo teste 4.
        4. Construir `RedirectResponse`/`Response` com `delete_cookie("__Host-session")`
           para forçar re-login (AC-6).
    - `/me/export` deve devolver um JSON com um dict top-level que contém
      entradas por tabela. `google_accounts` **nunca** deve incluir
      `refresh_token_encrypted` nem plaintext — apenas uma flag
      `has_refresh_token: bool`.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from app.services import crypto
from app.services.session_jwt import issue_session

# ---------------------------------------------------------------------------
# Constantes partilhadas
# ---------------------------------------------------------------------------

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
EMAIL = "test@per4biz.local"
COOKIE_NAME = "__Host-session"
FAKE_REFRESH_PLAINTEXT = b"1//fake_refresh"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_cookie() -> dict[str, str]:
    """Cookie de sessão válido para testes autenticados (SPEC §5.3).

    Emite um session JWT HS256 com o mesmo `USER_ID`/`EMAIL` que o conftest
    usa em `ALLOWED_USER_EMAIL`. O middleware injecta `{sub, email}` em
    `request.state.current_user`, permitindo que os endpoints /me resolvam
    a identidade sem contactar Supabase para auth.
    """
    token = issue_session(USER_ID, EMAIL)
    return {COOKIE_NAME: token}


def _build_supabase_mock_with_rows(rows_by_table: dict[str, list[dict[str, Any]]]) -> MagicMock:
    """Constrói um mock encadeável que devolve dados específicos por tabela.

    Suporta as cadeias usadas pelos endpoints /me:

        client.table("<t>").select("*").eq("user_id", uid).execute().data
        client.table("<t>").select("*").eq("id",      uid).execute().data
        client.table("<t>").delete().eq("user_id",    uid).execute()
        client.table("<t>").delete().eq("id",         uid).execute()

    Cada `.table(name)` devolve um sub-mock exclusivo por nome, para que
    possamos diferenciar o `.data` devolvido em `SELECT` entre tabelas.
    """
    client = MagicMock(name="supabase_client")

    sub_mocks: dict[str, MagicMock] = {}

    def _table_side_effect(name: str) -> MagicMock:
        if name not in sub_mocks:
            table_mock = MagicMock(name=f"supabase_table_{name}")
            rows = rows_by_table.get(name, [])
            # SELECT chain: .select(...).eq(...).execute().data == rows
            execute_result = MagicMock(data=rows)
            table_mock.select.return_value.eq.return_value.execute.return_value = execute_result
            # SELECT sem .eq (ex: .select("*").execute())
            table_mock.select.return_value.execute.return_value = execute_result
            # DELETE chain: .delete().eq(...).execute() -> ok
            delete_execute = MagicMock(data=[])
            table_mock.delete.return_value.eq.return_value.execute.return_value = delete_execute
            table_mock.delete.return_value.execute.return_value = delete_execute
            sub_mocks[name] = table_mock
        return sub_mocks[name]

    client.table.side_effect = _table_side_effect
    # Expor sub_mocks para os asserts por tabela
    client._sub_mocks = sub_mocks  # type: ignore[attr-defined]
    return client


# ---------------------------------------------------------------------------
# 1. GET /me — perfil básico (sem campos sensíveis)
# ---------------------------------------------------------------------------


def test_get_me_returns_profile(
    client, mocker: MockerFixture, auth_cookie: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """`GET /me` devolve o perfil do user logado (SPEC §5.5 profile view).

    Asserts:
        - 200 OK
        - JSON contém `id`, `email`, `created_at`
        - **NUNCA** inclui `refresh_token_encrypted` nem outros campos sensíveis
          (isolation entre /me e /me/export — este endpoint é "read-light").
    """
    user_row = {
        "id": str(USER_ID),
        "email": EMAIL,
        "created_at": "2026-04-15T12:00:00Z",
        "allowed": True,
    }
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock_with_rows({"users": [user_row]}),
    )

    response = client.get("/me", cookies=auth_cookie)

    assert response.status_code == 200, (
        f"esperado 200, recebido {response.status_code} (body: {response.text[:200]})"
    )
    body = response.json()
    assert body.get("id") == str(USER_ID), f"id ausente ou errado: {body}"
    assert body.get("email") == EMAIL, f"email ausente ou errado: {body}"
    assert "created_at" in body, f"created_at em falta: {body}"

    # Nunca vazar campos sensíveis
    forbidden_keys = {
        "refresh_token_encrypted",
        "access_token_encrypted",
        "refresh_token",
        "access_token",
    }
    leaked = forbidden_keys.intersection(body.keys())
    assert not leaked, f"GET /me vazou campos sensíveis: {leaked}"


# ---------------------------------------------------------------------------
# 2. GET /me/export — GDPR Art. 20 (portability)
# ---------------------------------------------------------------------------


def test_get_me_export_returns_json_dump_all_user_data(
    client, mocker: MockerFixture, auth_cookie: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """GDPR Art. 20 portability — `GET /me/export` devolve dump completo
    em formato estruturado, processável por máquina (JSON).

    Asserts:
        - 200 OK
        - JSON top-level tem keys `users`, `google_accounts`, `consent_log`,
          `app_settings` (mesmo que vazias — contrato estável).
        - `google_accounts[0]` tem `has_refresh_token: true` mas NUNCA expõe
          `refresh_token_encrypted` nem plaintext (sanitização obrigatória).
    """
    rows_by_table = {
        "users": [
            {
                "id": str(USER_ID),
                "email": EMAIL,
                "created_at": "2026-04-15T12:00:00Z",
                "allowed": True,
            }
        ],
        "google_accounts": [
            {
                "id": "ga-1",
                "user_id": str(USER_ID),
                "google_email": EMAIL,
                "refresh_token_encrypted": crypto.encrypt(FAKE_REFRESH_PLAINTEXT),
                "access_token_encrypted": crypto.encrypt(b"ya29.fake_access"),
                "access_token_expires_at": "2026-04-15T13:00:00Z",
                "scopes": ["openid", "email"],
                "is_primary": True,
                "key_version": 1,
            }
        ],
        "consent_log": [
            {
                "user_id": str(USER_ID),
                "policy_type": "privacy",
                "policy_version": "privacy-v1.0",
                "consent_given": True,
                "consented_at": "2026-04-15T12:00:00Z",
            }
        ],
        "app_settings": [
            {
                "user_id": str(USER_ID),
                "voice_enabled": True,
                "language": "pt-PT",
            }
        ],
    }
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock_with_rows(rows_by_table),
    )

    response = client.get("/me/export", cookies=auth_cookie)

    assert response.status_code == 200, (
        f"esperado 200, recebido {response.status_code} (body: {response.text[:200]})"
    )
    body = response.json()

    # Contrato: todas as 4 keys top-level presentes
    for key in ("users", "google_accounts", "consent_log", "app_settings"):
        assert key in body, f"export em falta key `{key}`: {list(body.keys())}"

    # google_accounts sanitizada
    assert len(body["google_accounts"]) == 1, "esperava 1 google_account"
    ga = body["google_accounts"][0]
    assert ga.get("has_refresh_token") is True, (
        f"google_accounts[0] deve ter `has_refresh_token: true`, foi {ga}"
    )
    forbidden = {"refresh_token_encrypted", "access_token_encrypted", "refresh_token"}
    leaked = forbidden.intersection(ga.keys())
    assert not leaked, f"export vazou campos sensíveis: {leaked}"

    # E no dump inteiro — garantir que o plaintext do refresh também não aparece
    raw_text = response.text
    assert "1//fake_refresh" not in raw_text, (
        "plaintext de refresh_token vazado em /me/export"
    )


# ---------------------------------------------------------------------------
# 3. DELETE /me — revoga tokens Google (AC-5)
# ---------------------------------------------------------------------------


def test_delete_me_revokes_google_tokens(
    client, mocker: MockerFixture, auth_cookie: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """AC-5 (SPEC §5.5 · revoke manual).

    `DELETE /me` deve chamar Google revoke endpoint com o refresh_token
    **em plaintext** (após decrypt). O specialist deve criar
    `app.services.google_oauth.revoke_token(refresh_token: str) -> None`
    que faz `POST https://oauth2.googleapis.com/revoke` — este teste
    mocka essa função e verifica o argumento.
    """
    encrypted_rt = crypto.encrypt(FAKE_REFRESH_PLAINTEXT)
    rows_by_table = {
        "users": [{"id": str(USER_ID), "email": EMAIL, "allowed": True}],
        "google_accounts": [
            {
                "id": "ga-1",
                "user_id": str(USER_ID),
                "google_email": EMAIL,
                "refresh_token_encrypted": encrypted_rt,
                "is_primary": True,
                "key_version": 1,
            }
        ],
        "consent_log": [],
        "app_settings": [],
    }
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock_with_rows(rows_by_table),
    )
    mock_revoke = mocker.patch(
        "app.services.google_oauth.revoke_token",
        return_value=None,
    )

    response = client.delete("/me", cookies=auth_cookie)

    assert response.status_code in (200, 204), (
        f"esperado 200/204, recebido {response.status_code} (body: {response.text[:200]})"
    )

    # Google revoke foi chamado pelo menos uma vez
    assert mock_revoke.called, "google_oauth.revoke_token não foi chamado"
    # Argumento deve ser o plaintext do refresh_token (após decrypt)
    args, kwargs = mock_revoke.call_args
    passed = args[0] if args else kwargs.get("refresh_token")
    assert passed == FAKE_REFRESH_PLAINTEXT.decode("utf-8"), (
        f"revoke_token recebeu {passed!r}, esperado plaintext "
        f"{FAKE_REFRESH_PLAINTEXT.decode('utf-8')!r} (decrypt falhou ou não foi feito)"
    )


# ---------------------------------------------------------------------------
# 4. DELETE /me — cascade delete em todas as tabelas
# ---------------------------------------------------------------------------


def test_delete_me_cascades_delete_all_tables(
    client, mocker: MockerFixture, auth_cookie: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """Cascade delete (GDPR Art. 17 right to erasure).

    Migration 0001 + 0004 declaram `ON DELETE CASCADE` nas FKs filhas
    (`google_accounts`, `email_cache`, `draft_responses`, `voice_sessions`,
    `consent_log`). Basta apagar em `users` para cascatar, mas o specialist
    pode optar por delete explícito por tabela (defence in depth).

    Este teste aceita ambas as estratégias: **exige** que `.table("users").delete(...)`
    seja chamado. Se o specialist preferir apagar filhas primeiro, óptimo —
    cobrimos esse cenário opcional via asserts mais fracos.
    """
    rows_by_table = {
        "users": [{"id": str(USER_ID), "email": EMAIL, "allowed": True}],
        "google_accounts": [
            {
                "id": "ga-1",
                "user_id": str(USER_ID),
                "google_email": EMAIL,
                "refresh_token_encrypted": crypto.encrypt(FAKE_REFRESH_PLAINTEXT),
                "is_primary": True,
                "key_version": 1,
            }
        ],
        "consent_log": [],
        "app_settings": [],
    }
    supabase_mock = _build_supabase_mock_with_rows(rows_by_table)
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=supabase_mock,
    )
    mocker.patch("app.services.google_oauth.revoke_token", return_value=None)

    response = client.delete("/me", cookies=auth_cookie)
    assert response.status_code in (200, 204), (
        f"esperado 200/204, recebido {response.status_code} (body: {response.text[:200]})"
    )

    # Obrigatório: `.table("users").delete(...).execute()` foi invocado
    users_table = supabase_mock._sub_mocks.get("users")
    assert users_table is not None, (
        "`.table(\"users\")` nunca foi pedido ao Supabase — cascade delete falhou"
    )
    assert users_table.delete.called, (
        "`.table(\"users\").delete(...)` não foi invocado — cascade delete em falta"
    )


# ---------------------------------------------------------------------------
# 5. DELETE /me — limpa cookie de sessão (AC-6 força re-login)
# ---------------------------------------------------------------------------


def test_delete_me_clears_cookie(
    client, mocker: MockerFixture, auth_cookie: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """AC-6 (SPEC §5.3 · cookie invalidado força re-login).

    Após `DELETE /me`, a response deve incluir `Set-Cookie: __Host-session=`
    com `Max-Age=0` (ou `expires=Thu, 01 Jan 1970 ...`) para que o browser
    descarte o cookie e o próximo request caia no 401 standard.
    """
    rows_by_table = {
        "users": [{"id": str(USER_ID), "email": EMAIL, "allowed": True}],
        "google_accounts": [
            {
                "id": "ga-1",
                "user_id": str(USER_ID),
                "google_email": EMAIL,
                "refresh_token_encrypted": crypto.encrypt(FAKE_REFRESH_PLAINTEXT),
                "is_primary": True,
                "key_version": 1,
            }
        ],
        "consent_log": [],
        "app_settings": [],
    }
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock_with_rows(rows_by_table),
    )
    mocker.patch("app.services.google_oauth.revoke_token", return_value=None)

    response = client.delete("/me", cookies=auth_cookie)

    assert response.status_code in (200, 204), (
        f"esperado 200/204, recebido {response.status_code}"
    )

    set_cookie = response.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie, (
        f"Set-Cookie header não contém `{COOKIE_NAME}`: {set_cookie!r}"
    )

    lower = set_cookie.lower()
    expired = ("max-age=0" in lower) or ("expires=" in lower and "1970" in lower)
    assert expired, (
        f"Set-Cookie não invalida a sessão (Max-Age=0 ou expires=1970 em falta): "
        f"{set_cookie!r}"
    )
