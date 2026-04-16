"""
Testes RED para `app.services.gmail` (Sprint 1.x · E2 · Task 1).

Módulo alvo:
    `app.services.gmail` (a criar na Task 2) — wrapper server-side do
    Gmail v1 API. Expõe:

        - `list_messages(user_id, page_token=None, limit=50) -> dict`
        - `get_message(user_id, message_id) -> dict`
        - `_get_valid_credentials(user_id) -> Credentials` (privada mas testável)
        - `_html_to_text(html: str) -> str` (stdlib HTMLParser)

ACs preparados:
    - AC-2.1 (listar 50 emails recentes — SPEC §6 / RF-2.1 + RF-2.6)
    - AC-2.2 (abrir email com body HTML strippado — SPEC §6)
    - AC-2.6 (token refresh silencioso quando `expired` — RF-2.1)
    - AC-2.7 (refresh_token revogado → `RefreshError` propagada — SPEC §6)

Enquanto `app/services/gmail.py` não existir, a colecção falha com
`ModuleNotFoundError: No module named 'app.services.gmail'` — RED
autêntica. Após GREEN (Task 2), os 5 testes passam sem alterar este
ficheiro.

Flags para o specialist (Task 2):
    - `from app.services.gmail import list_messages, get_message, _get_valid_credentials, _html_to_text`
    - Ordem de operações em `_get_valid_credentials`:
        1. `sb.table("google_accounts").select("*").eq("user_id", user_id).execute().data`
        2. Escolher primária (`is_primary=True`) ou primeira disponível
        3. `crypto.decrypt(refresh_token_encrypted)` → bytes → `.decode("utf-8")`
        4. `crypto.decrypt(access_token_encrypted)` → idem (pode ser `None`)
        5. Construir `google.oauth2.credentials.Credentials(token=..., refresh_token=...,
           token_uri="https://oauth2.googleapis.com/token", client_id=settings.GOOGLE_CLIENT_ID,
           client_secret=settings.GOOGLE_CLIENT_SECRET, scopes=[...])`
        6. Se `credentials.expired` (comparar com `access_token_expires_at` ou
           usar a própria flag da lib) → `credentials.refresh(Request())`
        7. Persistir novo `access_token` cifrado em `google_accounts` via
           `.upsert(...)` ou `.update(...).eq("id", ...)` com novo
           `access_token_expires_at = now + expires_in`
    - Propagar `google.auth.exceptions.RefreshError` raw (router trata 401+cleanup)
    - `_html_to_text` usa `html.parser.HTMLParser` stdlib — ignorar conteúdo
      dentro de `<script>` / `<style>`, normalizar whitespace, strip tags
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from google.auth.exceptions import RefreshError
from pytest_mock import MockerFixture

from app.services import crypto

# ---------------------------------------------------------------------------
# Constantes partilhadas
# ---------------------------------------------------------------------------

USER_ID = "00000000-0000-0000-0000-000000000001"
FAKE_REFRESH_PLAINTEXT = b"1//fake_refresh_token"
FAKE_ACCESS_PLAINTEXT = b"ya29.fake_access_token"


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def _build_google_account_row(
    *,
    access_expires_at: datetime | None = None,
    access_token_plaintext: bytes = FAKE_ACCESS_PLAINTEXT,
    refresh_token_plaintext: bytes = FAKE_REFRESH_PLAINTEXT,
) -> dict[str, Any]:
    """Row simulada de `google_accounts` com tokens cifrados realistas."""
    if access_expires_at is None:
        access_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return {
        "id": "ga-1",
        "user_id": USER_ID,
        "google_email": "jp@example.com",
        "refresh_token_encrypted": crypto.encrypt(refresh_token_plaintext),
        "access_token_encrypted": crypto.encrypt(access_token_plaintext),
        "access_token_expires_at": access_expires_at.isoformat(),
        "scopes": [
            "openid",
            "email",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
        "is_primary": True,
        "key_version": 1,
    }


def _build_supabase_mock_with_account(account_row: dict[str, Any]) -> MagicMock:
    """Mock encadeável do Supabase client que devolve `account_row`
    em `.table("google_accounts").select("*").eq(...).execute().data`.

    Também suporta chains de `update/upsert` para o refresh path:

        client.table("google_accounts").update({...}).eq("id", ga_id).execute()
        client.table("google_accounts").upsert({...}).execute()
    """
    client = MagicMock(name="supabase_client")
    table_mock = MagicMock(name="table_google_accounts")

    # SELECT chain (qualquer combinação de .eq(...) termina no mesmo execute)
    select_execute = MagicMock(data=[account_row])
    table_mock.select.return_value.eq.return_value.execute.return_value = select_execute
    table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
        select_execute
    )
    table_mock.select.return_value.execute.return_value = select_execute

    # UPDATE chain (refresh access_token_encrypted)
    update_execute = MagicMock(data=[])
    table_mock.update.return_value.eq.return_value.execute.return_value = update_execute

    # UPSERT chain (alternativa ao update)
    upsert_execute = MagicMock(data=[])
    table_mock.upsert.return_value.execute.return_value = upsert_execute

    client.table.return_value = table_mock
    client._table_mock = table_mock  # type: ignore[attr-defined]
    return client


def _b64url(data: bytes) -> str:
    """Base64 URL-safe encoding tal como a Gmail API entrega bodies."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _build_gmail_service_mock(
    *,
    list_response: dict[str, Any],
    get_responses: dict[str, dict[str, Any]],
) -> MagicMock:
    """Mock do objecto retornado por `googleapiclient.discovery.build(...)`.

    Suporta:
        service.users().messages().list(userId="me", maxResults=..., pageToken=..., q="in:inbox").execute()
            → `list_response`
        service.users().messages().get(userId="me", id=<id>, format=...).execute()
            → `get_responses[<id>]`
    """
    service = MagicMock(name="gmail_service")
    users = MagicMock(name="users")
    messages = MagicMock(name="messages")

    service.users.return_value = users
    users.messages.return_value = messages

    # list(...).execute() → list_response (qualquer combinação de kwargs)
    messages.list.return_value.execute.return_value = list_response

    # get(id=...).execute() → responde por id
    def _get_side_effect(**kwargs: Any) -> MagicMock:
        msg_id = kwargs.get("id")
        wrapper = MagicMock()
        wrapper.execute.return_value = get_responses.get(msg_id, {})
        return wrapper

    messages.get.side_effect = _get_side_effect

    return service


# ---------------------------------------------------------------------------
# 1. list_messages — happy path
# ---------------------------------------------------------------------------


def test_list_messages_returns_emails_for_user(mocker: MockerFixture) -> None:
    """AC-2.1 (SPEC §6) — `list_messages` devolve DTO com `emails` + `next_page_token`.

    Cada item cumpre RF-2.6: `id`, `from_name`, `from_email`, `subject`,
    `snippet`, `received_at`, `is_unread`.
    """
    account_row = _build_google_account_row()
    supabase_mock = _build_supabase_mock_with_account(account_row)
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=supabase_mock,
    )

    list_response = {
        "messages": [{"id": "msg1"}, {"id": "msg2"}],
        "nextPageToken": "tok2",
    }
    get_responses = {
        "msg1": {
            "id": "msg1",
            "snippet": "Primeiro snippet",
            "labelIds": ["INBOX", "UNREAD"],
            "internalDate": "1713182400000",  # 2024-04-15 ~12:00 UTC
            "payload": {
                "headers": [
                    {"name": "From", "value": "João Silva <joao@example.com>"},
                    {"name": "Subject", "value": "Proposta nova"},
                    {"name": "Date", "value": "Mon, 15 Apr 2024 12:00:00 +0000"},
                ]
            },
        },
        "msg2": {
            "id": "msg2",
            "snippet": "Segundo snippet",
            "labelIds": ["INBOX"],
            "internalDate": "1713168000000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Maria Pinto <maria@example.com>"},
                    {"name": "Subject", "value": "Reunião amanhã"},
                    {"name": "Date", "value": "Mon, 15 Apr 2024 08:00:00 +0000"},
                ]
            },
        },
    }
    gmail_service = _build_gmail_service_mock(
        list_response=list_response, get_responses=get_responses
    )
    mocker.patch("googleapiclient.discovery.build", return_value=gmail_service)

    from app.services.gmail import list_messages  # noqa: PLC0415 — RED import

    result = list_messages(USER_ID)

    assert "emails" in result, f"response sem key `emails`: {result}"
    assert "next_page_token" in result, f"response sem `next_page_token`: {result}"
    assert result["next_page_token"] == "tok2", (
        f"next_page_token errado: {result['next_page_token']!r}"
    )
    assert len(result["emails"]) == 2, f"esperados 2 emails, obtidos {len(result['emails'])}"

    required_keys = {
        "id",
        "from_name",
        "from_email",
        "subject",
        "snippet",
        "received_at",
        "is_unread",
    }
    for email in result["emails"]:
        missing = required_keys.difference(email.keys())
        assert not missing, f"email sem keys {missing}: {email}"


# ---------------------------------------------------------------------------
# 2. get_message — HTML stripped
# ---------------------------------------------------------------------------


def test_get_message_returns_body_html_stripped(mocker: MockerFixture) -> None:
    """AC-2.2 (SPEC §6) — `get_message` devolve `body_text` com HTML stripped.

    Gmail entrega o body em `payload.parts[].body.data` codificado em
    base64url. O wrapper deve decodificar e passar pelo `_html_to_text`
    stdlib para que o texto final seja apto a TTS.
    """
    account_row = _build_google_account_row()
    supabase_mock = _build_supabase_mock_with_account(account_row)
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=supabase_mock,
    )

    html_body = "<p>Olá <b>JP</b></p>"
    encoded_html = _b64url(html_body.encode("utf-8"))

    get_responses = {
        "msg1": {
            "id": "msg1",
            "snippet": "Olá JP",
            "labelIds": ["INBOX"],
            "internalDate": "1713182400000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "João Silva <joao@example.com>"},
                    {"name": "To", "value": "jp@example.com"},
                    {"name": "Subject", "value": "Olá"},
                    {"name": "Date", "value": "Mon, 15 Apr 2024 12:00:00 +0000"},
                ],
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {"data": encoded_html},
                    }
                ],
            },
        }
    }
    gmail_service = _build_gmail_service_mock(
        list_response={"messages": []}, get_responses=get_responses
    )
    mocker.patch("googleapiclient.discovery.build", return_value=gmail_service)

    from app.services.gmail import get_message  # noqa: PLC0415

    result = get_message(USER_ID, "msg1")

    assert "body_text" in result, f"response sem `body_text`: {result}"
    body = result["body_text"]
    # Essencial: sem tags HTML, conteúdo textual preservado.
    assert "Olá" in body, f"body não contém 'Olá': {body!r}"
    assert "JP" in body, f"body não contém 'JP': {body!r}"
    assert "<" not in body and ">" not in body, (
        f"body ainda contém tags HTML: {body!r}"
    )


# ---------------------------------------------------------------------------
# 3. Access token expirado → refresh + persist
# ---------------------------------------------------------------------------


def test_access_token_refresh_when_expired(mocker: MockerFixture) -> None:
    """AC-2.6 (SPEC §6 · RF-2.1) — access_token expirado é renovado silenciosamente.

    Flow esperado:
        1. `google_accounts.access_token_expires_at` está no passado.
        2. `_get_valid_credentials` detecta e chama `Credentials.refresh(Request())`.
        3. O novo `access_token` é cifrado e persistido em `google_accounts`
           junto com um novo `access_token_expires_at` no futuro.

    Mockamos `Credentials` inteiro para controlar `expired` e `refresh`.
    """
    expired_at = datetime.now(timezone.utc) - timedelta(hours=2)
    account_row = _build_google_account_row(access_expires_at=expired_at)
    supabase_mock = _build_supabase_mock_with_account(account_row)
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=supabase_mock,
    )

    # Mock do constructor de Credentials — devolve instância que se comporta como expirada,
    # e que ao `.refresh(Request())` actualiza `token` para o novo valor.
    fake_credentials = MagicMock(name="Credentials_instance")
    fake_credentials.expired = True
    fake_credentials.valid = False
    fake_credentials.token = FAKE_ACCESS_PLAINTEXT.decode("utf-8")

    def _refresh_side_effect(_request: Any) -> None:
        fake_credentials.token = "ya29.brand_new_access"  # noqa: S105 — fake token
        fake_credentials.expired = False
        fake_credentials.valid = True
        fake_credentials.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    fake_credentials.refresh.side_effect = _refresh_side_effect

    mocker.patch(
        "app.services.gmail.Credentials",
        return_value=fake_credentials,
    )
    # Evitar chamada real ao Gmail: o teste foca-se apenas no refresh path.
    mocker.patch(
        "googleapiclient.discovery.build",
        return_value=_build_gmail_service_mock(
            list_response={"messages": []},
            get_responses={},
        ),
    )

    from app.services.gmail import _get_valid_credentials  # noqa: PLC0415

    creds = _get_valid_credentials(USER_ID)

    # 1. refresh() foi de facto invocado
    assert fake_credentials.refresh.called, (
        "Credentials.refresh(Request()) não foi chamado — token expirado não foi renovado"
    )
    # 2. Credenciais devolvidas já têm o novo token
    assert creds.token == "ya29.brand_new_access", (
        f"access_token não foi actualizado após refresh: {creds.token!r}"
    )
    # 3. Supabase recebeu persistência do novo access_token_encrypted
    table_mock = supabase_mock._table_mock
    update_called = table_mock.update.called
    upsert_called = table_mock.upsert.called
    assert update_called or upsert_called, (
        "access_token renovado não foi persistido em `google_accounts` "
        "(.update(...) nem .upsert(...) invocados)"
    )

    # Extrai payload persistido (aceita update ou upsert)
    payload = None
    if update_called:
        args, kwargs = table_mock.update.call_args
        payload = args[0] if args else kwargs.get("values") or kwargs
    elif upsert_called:
        args, kwargs = table_mock.upsert.call_args
        payload = args[0] if args else kwargs.get("values") or kwargs

    assert payload is not None, "payload de persistência vazio"
    assert "access_token_encrypted" in payload, (
        f"payload persistido sem `access_token_encrypted`: {list(payload.keys())}"
    )
    # O ciphertext do novo token deve ser diferente do original
    assert payload["access_token_encrypted"] != account_row["access_token_encrypted"], (
        "access_token_encrypted persistido é igual ao anterior — refresh não gerou novo ciphertext"
    )


# ---------------------------------------------------------------------------
# 4. invalid_grant → RefreshError propagado
# ---------------------------------------------------------------------------


def test_invalid_grant_raises_specific_error(mocker: MockerFixture) -> None:
    """AC-2.7 (SPEC §6) — refresh_token revogado externamente propaga `RefreshError`.

    O router (`/emails/*`, Task 4) captura esta excepção para:
        - apagar `google_accounts` do user
        - limpar cookie `__Host-session`
        - devolver 401

    Aqui validamos apenas que o service **não engole** a excepção.
    """
    expired_at = datetime.now(timezone.utc) - timedelta(hours=2)
    account_row = _build_google_account_row(access_expires_at=expired_at)
    supabase_mock = _build_supabase_mock_with_account(account_row)
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=supabase_mock,
    )

    fake_credentials = MagicMock(name="Credentials_instance")
    fake_credentials.expired = True
    fake_credentials.valid = False
    fake_credentials.refresh.side_effect = RefreshError("invalid_grant")

    mocker.patch(
        "app.services.gmail.Credentials",
        return_value=fake_credentials,
    )

    from app.services.gmail import _get_valid_credentials  # noqa: PLC0415

    with pytest.raises(RefreshError, match="invalid_grant"):
        _get_valid_credentials(USER_ID)


# ---------------------------------------------------------------------------
# 5. _html_to_text — sanitização stdlib
# ---------------------------------------------------------------------------


def test_html_to_text_removes_tags_preserves_structure() -> None:
    """RF-2.1 · SPEC §4 — `_html_to_text` usa `html.parser.HTMLParser` stdlib.

    Critérios essenciais (validação flexível — whitespace fica ao critério
    do specialist na Task 2):
        - Tags HTML removidas (`<`, `>` ausentes do resultado).
        - Conteúdo dentro de `<script>` / `<style>` descartado.
        - Texto visível preservado.
    """
    from app.services.gmail import _html_to_text  # noqa: PLC0415

    # Caso 1: tags simples
    result1 = _html_to_text("<p>Olá <b>JP</b></p>")
    assert "Olá" in result1 and "JP" in result1, (
        f"texto visível perdido: {result1!r}"
    )
    assert "<" not in result1 and ">" not in result1, (
        f"tags não foram removidas: {result1!r}"
    )

    # Caso 2: quebras de linha (estrutura preservada minimamente —
    # aceita espaço OU newline entre blocos; o que interessa é não colar)
    result2 = _html_to_text("<div>Linha 1<br>Linha 2</div>")
    assert "Linha 1" in result2 and "Linha 2" in result2, (
        f"linhas perdidas: {result2!r}"
    )
    assert "<" not in result2, f"tags não removidas: {result2!r}"
    # Garantir que as duas linhas não ficaram coladas (algum separador entre elas)
    assert "Linha 1Linha 2" not in result2, (
        f"<br> não gerou separador entre linhas: {result2!r}"
    )

    # Caso 3: <script> deve ter conteúdo ignorado (não apenas tags removidas)
    result3 = _html_to_text("<script>alert('xss')</script>bom")
    assert "bom" in result3, f"texto visível perdido em caso 3: {result3!r}"
    assert "alert" not in result3, (
        f"conteúdo de <script> não foi ignorado: {result3!r}"
    )
    assert "<" not in result3, f"tags <script> não removidas: {result3!r}"

    # Caso 4: texto simples passa inalterado (modulo whitespace)
    result4 = _html_to_text("Texto simples sem tags")
    assert "Texto simples sem tags" in result4, (
        f"texto plain alterado indevidamente: {result4!r}"
    )
