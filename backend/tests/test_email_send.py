"""
Testes RED para `POST /emails/send` (Sprint 2 · E5 · Task 7 · SPEC §3 RF-V.4/V.5).

Endpoint alvo (a adicionar na Task 8 em `app/routers/emails.py`):

    @router.post("/emails/send")
    def send_email(req: SendEmailRequest, user: dict = _CurrentUser) -> dict:
        '''Envia email via Gmail + upsert draft_responses status=sent.'''

Service alvo (a adicionar na Task 8 em `app/services/gmail.py`):

    def send_message(
        user_id: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
    ) -> dict[str, Any]:
        '''Build RFC 5322 + Gmail `users.messages.send`; devolve
        {"message_id": str, "thread_id": str}.'''

ACs cobertos:
    - AC-E2.US3-1 (POST /emails/send envia via Gmail API e devolve
      `gmail_message_id` — 06-addendum/ACCEPTANCE-CRITERIA.md §E2.US3)
    - AC-E2.US3-3 (envio sucede → `draft_responses.status='sent'` +
      `sent_at=now()`)
    - AC-V.5 / RF-V.4 (SPEC §3 — build RFC 5322 → Gmail send)
    - AC-V.7 (erros — validação de payload inválido devolve 4xx)
    - AC-6 (SPEC §5.3 — auth obrigatória)

**Simplificação V1** (divergência intencional em relação a ACCEPTANCE-CRITERIA):
    O PLAN Task 8 (plans/e4-e5-voice-reply-send/PLAN.md) consolida o
    fluxo de E5 em `POST /emails/send {to, subject, body, in_reply_to?}`
    — payload directo do draft editável na UI (RF-V.8), sem passo
    intermédio de `/drafts/{id}/approve`. Logo, o teste
    `AC-E2.US3-2` (400 se draft não aprovado) **não se aplica** a V1 —
    o guardrail CLAUDE.md §3.7 "confirmação antes de enviar" é
    implementado UI-side (tap explícito em "Enviar" após review).

Enquanto o endpoint `/emails/send` não existir, todos os testes
abaixo falham com `404 Not Found` (happy paths e validação) ou com o
`mock` de `gmail.send_message` não sendo chamado — RED autêntica.

Flags para o specialist (Task 8):
    - **Pydantic EmailStr** em `to` exige `pydantic[email]` (dependência
      `email-validator`). Validar se já está em `pyproject.toml`; senão
      adicionar antes da GREEN.
    - **Schema `draft_responses`** (ver
      `supabase/migrations/0001_initial_schema.sql` linha 106): `to_emails`
      é `text[]`, `subject` é `text`, `body_text` é `text NOT NULL`,
      `status` é `draft_status` enum (`'sent'` é valor válido),
      `llm_model` é `NOT NULL` (em V1 sem LLM passar `llm_model='manual'`
      ou `'human_edited'` quando o body veio directo do textarea),
      `google_account_id` é `NOT NULL`. Para V1 single-tenant, o
      specialist pode fazer lookup pela conta primária do user_id
      (ver `app.services.gmail._select_primary_account`).
    - **RFC 5322 encoding** — usar `email.mime.text.MIMEText` + `Header`
      para subject unicode (PT-PT acentos). `send_message` deve fazer
      base64url-encode no `raw` antes de chamar
      `service.users().messages().send(userId='me', body={'raw': ...})`.
      Se `in_reply_to` presente, adicionar headers `In-Reply-To: <id>` +
      `References: <id>`.
    - **Propagação de `user["sub"]`** — o router passa `user["sub"]`
      como `user_id` para `send_message` (idem `list_messages`/
      `get_message`).
    - **Upsert em `draft_responses`** — chave natural pode ser
      (`user_id`, `reply_to_message_id`, `created_at`) ou usar INSERT
      simples (nova row por envio). PLAN Task 8 diz "Upsert"; aqui
      aceitamos qualquer um dos dois desde que o payload final tenha
      `status='sent'` + `sent_at` preenchido.
    - **invalid_grant** — tal como `/emails/list` / `/emails/{id}`, o
      envio deve capturar `google.auth.exceptions.RefreshError` e
      delegar em `_invalid_grant_response(user["sub"])` (teste separado
      pode ser adicionado em REFACTOR — ver §Edge Cases no final).
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest
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
    """Cookie de sessão válido para testes autenticados (SPEC §5.3)."""
    token = issue_session(USER_ID, EMAIL)
    return {COOKIE_NAME: token}


def _build_supabase_upsert_mock() -> MagicMock:
    """Mock encadeável para `client.table(t).upsert(payload).execute()`.

    Também cobre a variante `insert(...)` — o specialist escolhe em Task 8;
    o teste só verifica que uma das duas foi chamada em `draft_responses`
    com `status='sent'` + `sent_at` preenchido. Ver flags no topo do ficheiro.
    """
    client = MagicMock(name="supabase_client")
    table_mock = MagicMock(name="supabase_table")
    table_mock.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "d1"}])
    table_mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "d1"}])
    # Para o lookup de google_account_id primário (se specialist precisar).
    table_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "acc-1", "is_primary": True}]
    )
    client.table.return_value = table_mock
    return client


def _draft_payload_captured(supabase_mock: MagicMock) -> dict[str, Any]:
    """Extrai o payload do upsert/insert em `draft_responses`.

    Como o `_build_supabase_upsert_mock` devolve o mesmo `table_mock` para
    qualquer `.table(name)`, inspeccionamos ambas as listas de chamadas
    (`upsert.call_args_list` + `insert.call_args_list`) e devolvemos o
    primeiro payload que contenha a coluna `status='sent'`.
    """
    table_mock = supabase_mock.table.return_value
    all_calls = list(table_mock.upsert.call_args_list) + list(
        table_mock.insert.call_args_list
    )
    for call in all_calls:
        args, kwargs = call
        payload = args[0] if args else kwargs.get("data") or kwargs
        if isinstance(payload, dict) and payload.get("status") == "sent":
            return payload
    raise AssertionError(
        f"nenhum upsert/insert em draft_responses com status='sent' encontrado "
        f"(upserts={table_mock.upsert.call_args_list}, "
        f"inserts={table_mock.insert.call_args_list})"
    )


# ---------------------------------------------------------------------------
# 1. POST /emails/send — requer cookie de sessão (AC-6)
# ---------------------------------------------------------------------------


def test_send_requires_auth(client) -> None:  # type: ignore[no-untyped-def]
    """Sem cookie `__Host-session` a rota devolve 401 (SPEC §5.3 · AC-6).

    `SessionMiddleware` deixa `request.state.current_user=None`; a dep
    `current_user` converte isso em `HTTPException(401)`. O teste não
    deve disparar nenhuma chamada ao Gmail nem ao Supabase.
    """
    response = client.post(
        "/emails/send",
        json={"to": "x@y.z", "subject": "s", "body": "b"},
    )

    assert response.status_code == 401, (
        f"esperado 401 sem cookie, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )


# ---------------------------------------------------------------------------
# 2. POST /emails/send — happy path (AC-E2.US3-1 + AC-E2.US3-3 + RF-V.4/V.5)
# ---------------------------------------------------------------------------


def test_send_happy_path(
    client, mocker: MockerFixture, auth_cookies: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """AC-E2.US3-1 + AC-E2.US3-3 (06-addendum · ACCEPTANCE-CRITERIA.md §E2.US3).

    Cenário: user submete draft editado via `POST /emails/send` com
    `{to, subject, body}`. O endpoint deve:

        1. Chamar `gmail.send_message(user_sub, to, subject, body,
           in_reply_to=None)` — RF-V.4 (SPEC §3).
        2. Propagar o retorno `{message_id, thread_id}` como JSON 200.
        3. Upsert em `draft_responses` com `status='sent'` + `sent_at`
           preenchido — RF-V.5 + AC-E2.US3-3.

    Tudo isolado: gmail.send_message mockado (não fala com Google API);
    supabase admin client mockado (não fala com DB real).
    """
    # `create=True` permite patch antes de Task 8 criar `send_message` — o
    # RED honesto é "endpoint devolve 404/405" e não "AttributeError no
    # patch setup". Após GREEN, o `create=True` é inofensivo (o atributo
    # já existe e o mock substitui-o normalmente).
    mock_send = mocker.patch(
        "app.services.gmail.send_message",
        return_value={"message_id": "m42", "thread_id": "t7"},
        create=True,
    )
    supabase_mock = _build_supabase_upsert_mock()
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=supabase_mock,
    )

    payload = {
        "to": "joao@example.com",
        "subject": "Re: Teste",
        "body": "Obrigado.",
    }
    response = client.post("/emails/send", json=payload, cookies=auth_cookies)

    # 2.1 — Status + shape JSON
    assert response.status_code == 200, (
        f"esperado 200, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )
    body = response.json()
    assert body == {"message_id": "m42", "thread_id": "t7"}, (
        f"JSON de resposta inesperado: {body}"
    )

    # 2.2 — gmail.send_message chamado com user_id canónico + payload + kwarg
    # `in_reply_to=None` (default, visto que não foi passado no payload).
    mock_send.assert_called_once_with(
        USER_ID_STR,
        "joao@example.com",
        "Re: Teste",
        "Obrigado.",
        in_reply_to=None,
    )

    # 2.3 — draft_responses recebeu upsert/insert com status='sent' + sent_at
    assert supabase_mock.table.called, (
        "Supabase `.table(...)` não foi invocado — upsert draft_responses em falta"
    )
    supabase_mock.table.assert_any_call("draft_responses")

    draft_payload = _draft_payload_captured(supabase_mock)
    assert draft_payload.get("status") == "sent", (
        f"draft_responses.status != 'sent': {draft_payload}"
    )
    assert draft_payload.get("sent_at"), (
        f"draft_responses.sent_at não preenchido: {draft_payload}"
    )


# ---------------------------------------------------------------------------
# 3. POST /emails/send — reply threading com in_reply_to (RF-V.4)
# ---------------------------------------------------------------------------


def test_send_with_in_reply_to(
    client, mocker: MockerFixture, auth_cookies: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """RF-V.4 (SPEC §3) — `in_reply_to` opcional propaga como kwarg.

    Quando o user responde a um email, o frontend envia `in_reply_to`
    com o `gmail_message_id` original. O router deve propagar esse
    valor 1:1 como kwarg para `gmail.send_message` — que em Task 8
    vai adicionar os headers RFC 5322 `In-Reply-To: <prev-msg-id>` +
    `References: <prev-msg-id>` no MIME construído.
    """
    mock_send = mocker.patch(
        "app.services.gmail.send_message",
        return_value={"message_id": "m99", "thread_id": "t9"},
        create=True,
    )
    supabase_mock = _build_supabase_upsert_mock()
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=supabase_mock,
    )

    payload = {
        "to": "joao@example.com",
        "subject": "Re: Reunião",
        "body": "Confirmo presença.",
        "in_reply_to": "prev-msg-id",
    }
    response = client.post("/emails/send", json=payload, cookies=auth_cookies)

    assert response.status_code == 200, (
        f"esperado 200, recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )

    # Verifica kwarg explicitamente — é a API pública de `send_message`.
    mock_send.assert_called_once_with(
        USER_ID_STR,
        "joao@example.com",
        "Re: Reunião",
        "Confirmo presença.",
        in_reply_to="prev-msg-id",
    )


# ---------------------------------------------------------------------------
# 4. POST /emails/send — rejeita email inválido (Pydantic EmailStr)
# ---------------------------------------------------------------------------


def test_send_rejects_invalid_email(
    client, mocker: MockerFixture, auth_cookies: dict[str, str]  # type: ignore[no-untyped-def]
) -> None:
    """Validação Pydantic — `to` deve ser `EmailStr` (AC-V.7 · SPEC §6).

    Cenário: payload com `to` mal formado ("not-an-email") deve ser
    rejeitado pelo FastAPI com 422 ANTES do handler correr. Nem a
    Gmail API nem o Supabase podem ser tocados — a validação é a
    primeira linha de defesa contra payloads inválidos (ERROR-MATRIX:
    "Draft sem destinatário / inválido → 422 client-side").

    Flag para specialist (Task 8): usar `pydantic.EmailStr` em
    `SendEmailRequest.to`. Requer `email-validator` instalado
    (verifica `pyproject.toml`; adicionar ao dependency list se ausente).
    """
    mock_send = mocker.patch(
        "app.services.gmail.send_message",
        return_value={"message_id": "NEVER", "thread_id": "NEVER"},
        create=True,
    )
    # Supabase mock defensivo — se o specialist se esquecer de validar e
    # o handler correr, queremos detectar via `not_called` (falha clara).
    supabase_mock = _build_supabase_upsert_mock()
    mocker.patch(
        "app.services.supabase_client.get_supabase_admin",
        return_value=supabase_mock,
    )

    payload = {
        "to": "not-an-email",
        "subject": "s",
        "body": "b",
    }
    response = client.post("/emails/send", json=payload, cookies=auth_cookies)

    assert response.status_code == 422, (
        f"esperado 422 (validação Pydantic), recebido {response.status_code} "
        f"(body: {response.text[:200]})"
    )

    # Gmail NUNCA pode ser chamado com email inválido — defesa contra
    # envios acidentais a endereços malformados (CLAUDE.md §3.7).
    mock_send.assert_not_called()
