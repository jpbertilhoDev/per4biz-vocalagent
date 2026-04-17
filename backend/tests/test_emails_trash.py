"""Tests for ``POST /emails/{id}/trash`` (Sprint V1 polish · F-Delete).

Covers:
    - happy path: service is called with correct args, response propagates
      ``{id, labelIds}`` verbatim.
    - 404 from Gmail → router returns ``404 email_not_found``.
    - auth guard: no cookie → 401/403 (SessionMiddleware / current_user dep).

Mirrors the mocking/cookie conventions used in ``test_emails_endpoints.py``:
session JWT issued via ``app.services.session_jwt.issue_session`` and
``app.services.gmail.trash_message`` patched to avoid touching Google /
Supabase.
"""
from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import httplib2
import pytest
from app.services.session_jwt import issue_session
from googleapiclient.errors import HttpError

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
EMAIL = "test@per4biz.local"
COOKIE_NAME = "__Host-session"


@pytest.fixture
def auth_cookies() -> dict[str, str]:
    """Cookie de sessão válido (mesmo pattern que ``test_emails_endpoints.py``)."""
    token = issue_session(USER_ID, EMAIL)
    return {COOKIE_NAME: token}


def test_trash_email_success(client, auth_cookies: dict[str, str]) -> None:  # type: ignore[no-untyped-def]
    """Happy path: `trash_message` devolve `{id, labelIds}` e o endpoint propaga."""
    with patch("app.services.gmail.trash_message") as mock_trash:
        mock_trash.return_value = {"id": "abc123", "labelIds": ["TRASH"]}
        resp = client.post("/emails/abc123/trash", cookies=auth_cookies)

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"id": "abc123", "labelIds": ["TRASH"]}
    mock_trash.assert_called_once()
    # Positional or kwargs — aceitamos ambos
    args, kwargs = mock_trash.call_args
    all_args = list(args) + list(kwargs.values())
    assert "abc123" in all_args, f"message_id não chegou ao service: {args} {kwargs}"


def test_trash_email_not_found(client, auth_cookies: dict[str, str]) -> None:  # type: ignore[no-untyped-def]
    """Gmail 404 → router devolve 404 com detail `email_not_found`."""
    fake_resp = httplib2.Response({"status": "404"})
    fake_resp.reason = "Not Found"
    with patch("app.services.gmail.trash_message") as mock_trash:
        mock_trash.side_effect = HttpError(
            fake_resp, b'{"error": {"message": "Not Found"}}'
        )
        resp = client.post("/emails/nope/trash", cookies=auth_cookies)

    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == "email_not_found"


def test_trash_requires_auth(client) -> None:  # type: ignore[no-untyped-def]
    """Sem cookie `__Host-session` a rota rejeita (401 via current_user dep)."""
    resp = client.post("/emails/abc/trash")
    assert resp.status_code in (401, 403), (
        f"esperado 401/403 sem cookie, recebido {resp.status_code} "
        f"(body: {resp.text[:200]})"
    )
