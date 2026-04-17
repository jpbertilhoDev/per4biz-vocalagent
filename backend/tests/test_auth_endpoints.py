"""
Testes RED para os endpoints OAuth Google (Sprint 1 · E1 · Task 7).

Cobrem:
- `GET /auth/google/start`   → redirect para Google com state JWT (SPEC §4.1 passo 3)
- `GET /auth/google/callback` → troca code→tokens, gating ALLOWED_USER_EMAIL,
  cifra AES-256-GCM, upsert em `users` + `google_accounts` + `consent_log`,
  emite cookie `__Host-session` e redireciona para `/inbox` (SPEC §4.1).

ACs alvo (SPEC §7):
- AC-1 (primeiro login bem-sucedido)
- AC-2 (login cancelado)
- AC-7 (CSRF no callback — state inválido rejeitado)
- AC-8 (tokens nunca em logs)
- Gating `ALLOWED_USER_EMAIL` (V1 single-tenant, SPEC §4.1 passo 6)

Enquanto `app/routers/auth.py`, `app/services/google_oauth.py` e
`app/services/supabase_client.py` não existirem, a collection falha com
`ModuleNotFoundError` — RED autêntica (PLAN Track 2 · Task 7).

Mock strategy: `pytest-mock` (`mocker`) patcha as 2 helpers que o router
`auth` vai invocar (`exchange_code_for_tokens`, `fetch_userinfo`) e o factory
`get_supabase_admin`. Cadeia Supabase encenada com `MagicMock` para permitir
`.table(...).upsert(...).execute()` e `.table(...).insert(...).execute()`.
"""
from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from app.services.crypto import decrypt
from app.services.state_jwt import sign_state
from tests.fixtures.google_oauth_mocks import (
    FAKE_TOKENS,
    FAKE_USERINFO_MATCH,
    FAKE_USERINFO_MISMATCH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_supabase_mock() -> MagicMock:
    """Cria um mock encadeável que replica a API `supabase-py`.

    Suporta:
        client.table("users").upsert({...}).execute()
        client.table("google_accounts").upsert({...}).execute()
        client.table("consent_log").insert({...}).execute()

    Cada `.table(name)` devolve sempre o MESMO sub-mock (por nome), para
    permitir inspeccionar chamadas via `mock.table.return_value.upsert.call_args_list`
    e também via `mock.table.call_args_list` (lista de nomes de tabela).
    """
    client = MagicMock(name="supabase_client")
    # `table` é chamado com o nome da tabela. Reutilizamos o mesmo child mock
    # para todos os nomes — PLAN Task 8 deixa em aberto se o specialist
    # prefere 1 sub-mock por tabela. Os asserts usam `assert_any_call("<name>")`.
    table_mock = MagicMock(name="supabase_table")
    table_mock.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "x"}])
    table_mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "x"}])
    client.table.return_value = table_mock
    return client


def _upsert_payload_for(mock_supabase_factory: MagicMock, table_name: str) -> dict[str, Any]:
    """Extrai o 1º arg positional de `.upsert(...)` para a tabela indicada.

    Faz walk em `client.table.call_args_list` encontrando o i-ésimo call
    cujo 1º arg == `table_name`, e devolve o payload do upsert/insert
    correspondente capturado pela cadeia.
    """
    client = mock_supabase_factory.return_value
    # Como todas as chamadas `table(...)` devolvem o mesmo sub-mock, basta olhar
    # para `upsert.call_args_list` — mas precisamos filtrar por tabela: o
    # specialist vai alternar `upsert`/`insert` entre tabelas. Aqui devolvemos
    # o primeiro payload de upsert observado (os testes usam isto apenas para
    # `google_accounts`, a única tabela sobre a qual se inspecciona payload).
    # Se futuramente 2 tabelas usarem upsert, refinar para (table_name, call_idx).
    assert client.table.called, "Supabase `.table(...)` não foi invocado"
    # Devolve o 1º arg do 1º upsert — specialist deve cifrar antes de upsert.
    first_upsert = client.table.return_value.upsert.call_args_list[0]
    args, _kwargs = first_upsert
    payload = args[0] if args else _kwargs.get("data")
    assert isinstance(payload, dict), f"upsert payload para {table_name} não é dict"
    return payload


# ---------------------------------------------------------------------------
# 1. /auth/google/start
# ---------------------------------------------------------------------------


def test_start_redirects_to_google_with_state(client) -> None:  # type: ignore[no-untyped-def]
    """AC-1 / SPEC §4.1 passo 3 · R-E1.5 do PLAN.

    `GET /auth/google/start` deve redirecionar 307 para o endpoint OAuth
    da Google com todos os query params exigidos: `client_id`, `redirect_uri`,
    `state` (JWT HS256), `scope` (4 scope groups), `response_type=code`,
    `access_type=offline` e `prompt=consent` (R-E1.5: garante refresh_token
    em cada consent).
    """
    response = client.get("/auth/google/start", follow_redirects=False)

    assert response.status_code == 307, (
        f"esperado 307 redirect, recebido {response.status_code}"
    )
    location = response.headers.get("location", "")
    assert "accounts.google.com/o/oauth2/v2/auth" in location, (
        f"location não aponta para Google OAuth: {location}"
    )
    # Query params obrigatórios
    for param in (
        "client_id=",
        "redirect_uri=",
        "state=",
        "scope=",
        "response_type=code",
        "access_type=offline",
        "prompt=consent",
    ):
        assert param in location, f"param `{param}` em falta em {location}"


# ---------------------------------------------------------------------------
# 2. /auth/google/callback — happy path
# ---------------------------------------------------------------------------


def test_callback_happy_path_creates_accounts_rows(
    client, mocker: MockerFixture  # type: ignore[no-untyped-def]
) -> None:
    """AC-1 completo (SPEC §4.1 passos 5-7).

    Com state JWT válido, email coincide com `ALLOWED_USER_EMAIL`, tokens
    trocados com sucesso → insere/upsert em `users`, `google_accounts` e
    `consent_log`, emite cookie `__Host-session` e redireciona (307) para
    `/inbox` ou `/auth/loading` (PLAN Task 16 permite splash intermédio).
    """
    state = sign_state("/inbox")
    mock_exchange = mocker.patch(
        "app.services.google_oauth.exchange_code_for_tokens",
        return_value=FAKE_TOKENS,
    )
    mock_fetch = mocker.patch(
        "app.services.google_oauth.fetch_userinfo",
        return_value=FAKE_USERINFO_MATCH,
    )
    mock_supabase_factory = mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock(),
    )

    response = client.get(
        f"/auth/google/callback?code=fake_code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 307, (
        f"esperado 307 redirect pós-callback, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )
    location = response.headers.get("location", "")
    # Backend redireciona para origem do frontend (cross-origin) — path pode estar absoluto.
    # Após adicionar fallback Authorization header, a URL leva `#session=<jwt>` no
    # fragmento para o frontend armazenar em localStorage.
    location_path = location.split("#", 1)[0]
    assert location_path.endswith("/inbox") or location_path.endswith("/auth/loading"), (
        f"redirect esperado para /inbox ou /auth/loading, foi {location}"
    )
    assert "#session=" in location, (
        f"redirect deve incluir fragmento #session=<jwt> para fallback Authorization header; foi {location}"
    )

    # Cookie de sessão emitido (SPEC §5.4 · RF-1.2)
    set_cookie = response.headers.get("set-cookie", "")
    assert "__Host-session" in set_cookie or "__Host-per4biz_session" in set_cookie, (
        f"cookie de sessão `__Host-session` ausente: {set_cookie}"
    )

    # Exchange + userinfo foram chamados exactamente uma vez
    mock_exchange.assert_called_once()
    mock_fetch.assert_called_once()

    # Supabase: `users`, `google_accounts` e `consent_log` foram tocadas
    supabase_client = mock_supabase_factory.return_value
    tables_called = [c.args[0] for c in supabase_client.table.call_args_list if c.args]
    assert "users" in tables_called, f"tabela users não foi tocada: {tables_called}"
    assert "google_accounts" in tables_called, (
        f"tabela google_accounts não foi tocada: {tables_called}"
    )
    assert "consent_log" in tables_called, (
        f"tabela consent_log não foi tocada: {tables_called}"
    )


# ---------------------------------------------------------------------------
# 3. /auth/google/callback — email mismatch → 403
# ---------------------------------------------------------------------------


def test_callback_rejects_mismatched_email(
    client, mocker: MockerFixture  # type: ignore[no-untyped-def]
) -> None:
    """Gating ALLOWED_USER_EMAIL (V1 single-tenant · CLAUDE.md §3 regra 8).

    Se `id_token.email` (ou userinfo.email) ≠ `ALLOWED_USER_EMAIL` → 403
    antes de QUALQUER escrita em Supabase. Única barreira de auth em V1.
    """
    state = sign_state("/inbox")
    mocker.patch(
        "app.services.google_oauth.exchange_code_for_tokens",
        return_value=FAKE_TOKENS,
    )
    mocker.patch(
        "app.services.google_oauth.fetch_userinfo",
        return_value=FAKE_USERINFO_MISMATCH,  # attacker@evil.com
    )
    mock_supabase_factory = mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock(),
    )

    response = client.get(
        f"/auth/google/callback?code=fake_code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 403, (
        f"esperado 403 para email não autorizado, recebido {response.status_code}"
    )
    # Mensagem deve mencionar email/não autorizado (sem vazar o email recebido)
    body_lower = response.text.lower()
    assert "email" in body_lower or "not allowed" in body_lower or "não autorizado" in body_lower

    # Zero escritas em Supabase
    mock_supabase_factory.return_value.table.assert_not_called()


# ---------------------------------------------------------------------------
# 4. /auth/google/callback — state inválido → 400 (AC-7 CSRF)
# ---------------------------------------------------------------------------


def test_callback_rejects_invalid_state(
    client, mocker: MockerFixture  # type: ignore[no-untyped-def]
) -> None:
    """AC-7 (SPEC §5.3 CSRF).

    State malformado/não assinado com o secret correcto → 400 "Invalid state"
    ANTES de qualquer tentativa de trocar o code por tokens.
    """
    mock_exchange = mocker.patch(
        "app.services.google_oauth.exchange_code_for_tokens",
        return_value=FAKE_TOKENS,
    )
    mock_supabase_factory = mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock(),
    )

    response = client.get(
        "/auth/google/callback?code=fake_code&state=invalidgarbage",
        follow_redirects=False,
    )

    assert response.status_code == 400, (
        f"esperado 400 para state inválido, recebido {response.status_code}"
    )
    mock_exchange.assert_not_called()
    mock_supabase_factory.return_value.table.assert_not_called()


# ---------------------------------------------------------------------------
# 5. /auth/google/callback — refresh_token cifrado AES-256-GCM (SPEC §5.1)
# ---------------------------------------------------------------------------


def test_callback_encrypts_refresh_token(
    client, mocker: MockerFixture  # type: ignore[no-untyped-def]
) -> None:
    """SPEC §5.1 · AC-1 — refresh_token gravado em `google_accounts` TEM de
    estar cifrado AES-256-GCM; decifrar tem de devolver o plaintext original.
    """
    state = sign_state("/inbox")
    mocker.patch(
        "app.services.google_oauth.exchange_code_for_tokens",
        return_value=FAKE_TOKENS,
    )
    mocker.patch(
        "app.services.google_oauth.fetch_userinfo",
        return_value=FAKE_USERINFO_MATCH,
    )
    mock_supabase_factory = mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock(),
    )

    response = client.get(
        f"/auth/google/callback?code=fake_code&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 307

    # Localizar o upsert em `google_accounts` inspeccionando table.call_args_list
    supabase_client = mock_supabase_factory.return_value
    upsert_calls = supabase_client.table.return_value.upsert.call_args_list
    assert upsert_calls, "nenhum `.upsert(...)` foi invocado em Supabase"

    # Procurar payload que contenha `refresh_token_encrypted`
    encrypted_payload: dict[str, Any] | None = None
    for call in upsert_calls:
        args, kwargs = call
        payload = args[0] if args else kwargs.get("data")
        if isinstance(payload, dict) and "refresh_token_encrypted" in payload:
            encrypted_payload = payload
            break
    assert encrypted_payload is not None, (
        "nenhum upsert contém a coluna `refresh_token_encrypted`"
    )

    ciphertext_str = encrypted_payload["refresh_token_encrypted"]
    plaintext_bytes = FAKE_TOKENS["refresh_token"].encode()

    # Postgrest bytea input format: string "\\x<hex>" (escape final \x em Python literal)
    assert isinstance(ciphertext_str, str), (
        f"refresh_token_encrypted deve ser str (hex \\\\x format), foi {type(ciphertext_str).__name__}"
    )
    assert ciphertext_str.startswith("\\x"), (
        f"refresh_token_encrypted deve começar com '\\\\x', foi {ciphertext_str[:4]!r}"
    )
    ciphertext = bytes.fromhex(ciphertext_str[2:])
    assert ciphertext != plaintext_bytes, (
        "refresh_token_encrypted coincide com o plaintext — NÃO foi cifrado"
    )
    # Round-trip: decifrar deve devolver o refresh_token original
    assert decrypt(ciphertext) == plaintext_bytes, (
        "decrypt(refresh_token_encrypted) não devolve o plaintext original"
    )


# ---------------------------------------------------------------------------
# 6. /auth/google/callback — insere consent_log (privacy-v1.0)
# ---------------------------------------------------------------------------


def test_callback_inserts_consent_log_row(
    client, mocker: MockerFixture  # type: ignore[no-untyped-def]
) -> None:
    """SPEC §5.5 · migration 0004 — insere linha em `consent_log` com
    `policy_type='privacy'`, `policy_version='privacy-v1.0'`, `consent_given=true`.
    """
    state = sign_state("/inbox")
    mocker.patch(
        "app.services.google_oauth.exchange_code_for_tokens",
        return_value=FAKE_TOKENS,
    )
    mocker.patch(
        "app.services.google_oauth.fetch_userinfo",
        return_value=FAKE_USERINFO_MATCH,
    )
    mock_supabase_factory = mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock(),
    )

    response = client.get(
        f"/auth/google/callback?code=fake_code&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 307

    supabase_client = mock_supabase_factory.return_value
    # Garante que `.table("consent_log")` foi pedida
    table_names = [c.args[0] for c in supabase_client.table.call_args_list if c.args]
    assert "consent_log" in table_names, (
        f"`.table(\"consent_log\")` não foi chamada: {table_names}"
    )

    # Localizar payload de consent_log (insert OU upsert — specialist escolhe)
    all_payload_calls = (
        supabase_client.table.return_value.insert.call_args_list
        + supabase_client.table.return_value.upsert.call_args_list
    )
    consent_payload: dict[str, Any] | None = None
    for call in all_payload_calls:
        args, kwargs = call
        payload = args[0] if args else kwargs.get("data")
        if isinstance(payload, dict) and payload.get("policy_type") == "privacy":
            consent_payload = payload
            break

    assert consent_payload is not None, (
        "nenhum insert/upsert com `policy_type='privacy'` encontrado"
    )
    assert consent_payload.get("policy_version") == "privacy-v1.0", (
        f"policy_version esperada 'privacy-v1.0', foi {consent_payload.get('policy_version')}"
    )
    assert consent_payload.get("consent_given") is True, (
        f"consent_given deve ser True, foi {consent_payload.get('consent_given')}"
    )
    assert "user_id" in consent_payload, "consent_log precisa de user_id"


# ---------------------------------------------------------------------------
# 7. /auth/google/callback — tokens NUNCA em logs (AC-8)
# ---------------------------------------------------------------------------


def test_logs_never_contain_tokens(
    client, mocker: MockerFixture, caplog: pytest.LogCaptureFixture  # type: ignore[no-untyped-def]
) -> None:
    """AC-8 (SPEC §5.2 + LOGGING-POLICY) — nenhum access/refresh/id token
    em texto claro nos logs, mesmo em DEBUG.
    """
    caplog.set_level(logging.DEBUG)

    state = sign_state("/inbox")
    mocker.patch(
        "app.services.google_oauth.exchange_code_for_tokens",
        return_value=FAKE_TOKENS,
    )
    mocker.patch(
        "app.services.google_oauth.fetch_userinfo",
        return_value=FAKE_USERINFO_MATCH,
    )
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock(),
    )

    response = client.get(
        f"/auth/google/callback?code=fake_code&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 307

    log_text = caplog.text
    assert FAKE_TOKENS["access_token"] not in log_text, (
        "access_token vazado em logs — AC-8 violado"
    )
    assert FAKE_TOKENS["refresh_token"] not in log_text, (
        "refresh_token vazado em logs — AC-8 violado"
    )
    assert FAKE_TOKENS["id_token"] not in log_text, (
        "id_token vazado em logs — AC-8 violado"
    )


# ---------------------------------------------------------------------------
# 8. /auth/google/callback — cancel (?error=access_denied) → redirect home
# ---------------------------------------------------------------------------


def test_callback_cancel_redirects_home(
    client, mocker: MockerFixture  # type: ignore[no-untyped-def]
) -> None:
    """AC-2 (SPEC §4.2) — utilizador cancela no Google consent.

    Callback recebido com `?error=access_denied` deve redirecionar 307 para
    `/` (ou `/?error=access_denied` para toast no frontend), sem escrever
    em Supabase nem emitir cookie de sessão.
    """
    state = sign_state("/inbox")
    mock_exchange = mocker.patch(
        "app.services.google_oauth.exchange_code_for_tokens",
        return_value=FAKE_TOKENS,
    )
    mock_supabase_factory = mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=_build_supabase_mock(),
    )

    response = client.get(
        f"/auth/google/callback?error=access_denied&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 307, (
        f"esperado 307 em cancel, recebido {response.status_code}"
    )
    location = response.headers.get("location", "")
    assert location == "/" or location.startswith("/?"), (
        f"esperado redirect para `/` em cancel, foi {location}"
    )

    mock_exchange.assert_not_called()
    mock_supabase_factory.return_value.table.assert_not_called()
    # Cookie de sessão NÃO deve ser emitido
    set_cookie = response.headers.get("set-cookie", "")
    assert "__Host-session" not in set_cookie and "__Host-per4biz_session" not in set_cookie, (
        f"cookie de sessão emitido em cancel: {set_cookie}"
    )
