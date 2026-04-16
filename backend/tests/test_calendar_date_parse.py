"""Integration: /calendar/events normalizes PT natural-language dates.

Guards the safety-net behaviour wired into `app/routers/calendar.py`:
    - PT inputs like "amanhã às 10h" are converted to ISO before being
      forwarded to `calendar.create_event`.
    - Unparseable `start` returns HTTP 400 `invalid_start_date`.
    - Empty/unparseable `end` falls back to `start + 1h`.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from app.services.session_jwt import issue_session
from pytest_mock import MockerFixture

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
EMAIL = "test@per4biz.local"
COOKIE_NAME = "__Host-session"


@pytest.fixture
def auth_cookies() -> dict[str, str]:
    """Cookie `__Host-session` válido — mesmo padrão de test_emails_endpoints.py."""
    token = issue_session(USER_ID, EMAIL)
    return {COOKIE_NAME: token}


def _fake_event() -> dict[str, Any]:
    return {
        "id": "abc123",
        "summary": "Teste",
        "start": "2026-04-18T10:00:00+01:00",
        "end": "2026-04-18T11:00:00+01:00",
        "is_all_day": False,
        "description": "",
        "location": "",
        "attendees": [],
        "status": "confirmed",
        "html_link": "https://calendar.google.com/event?eid=abc123",
    }


def test_create_event_requires_auth(client) -> None:  # type: ignore[no-untyped-def]
    """Sem cookie de sessão → 401 (baseline de protecção)."""
    response = client.post(
        "/calendar/events",
        json={"summary": "Teste", "start": "amanhã às 10h"},
    )
    assert response.status_code == 401


def test_create_event_normalizes_natural_language_start(
    client,  # type: ignore[no-untyped-def]
    mocker: MockerFixture,
    auth_cookies: dict[str, str],
) -> None:
    """POST /calendar/events com 'amanhã às 10h' deve chegar ISO ao service.

    O LLM por vezes emite strings PT cruas; o router tem um safety-net que
    normaliza via `parse_pt_datetime` antes de chamar `calendar.create_event`.
    """
    mock_create = mocker.patch(
        "app.services.calendar.create_event",
        return_value=_fake_event(),
    )

    response = client.post(
        "/calendar/events",
        json={"summary": "Teste", "start": "amanhã às 10h", "end": ""},
        cookies=auth_cookies,
    )
    assert response.status_code in (200, 201), response.text

    kwargs = mock_create.call_args.kwargs
    # start foi normalizado para ISO — contém 'T' e deve parsear-se como ISO
    assert "T" in kwargs["start"], f"start não veio ISO: {kwargs['start']}"
    from datetime import datetime

    start_dt = datetime.fromisoformat(kwargs["start"])
    # "amanhã às 10h" → hora 10
    assert start_dt.hour == 10, f"hora errada: {start_dt}"
    # end vazio → fallback start + 1h
    end_dt = datetime.fromisoformat(kwargs["end"])
    assert end_dt.hour == 11, f"fallback end+1h falhou: {end_dt}"


def test_create_event_passes_through_valid_iso(
    client,  # type: ignore[no-untyped-def]
    mocker: MockerFixture,
    auth_cookies: dict[str, str],
) -> None:
    """ISO válido passa inalterado (ignoring só tz normalization)."""
    mock_create = mocker.patch(
        "app.services.calendar.create_event",
        return_value=_fake_event(),
    )
    response = client.post(
        "/calendar/events",
        json={
            "summary": "Teste",
            "start": "2026-04-23T15:00:00+01:00",
            "end": "2026-04-23T16:00:00+01:00",
        },
        cookies=auth_cookies,
    )
    assert response.status_code in (200, 201), response.text
    kwargs = mock_create.call_args.kwargs
    from datetime import datetime

    assert datetime.fromisoformat(kwargs["start"]).hour == 15
    assert datetime.fromisoformat(kwargs["end"]).hour == 16


def test_create_event_rejects_unparseable_start(
    client,  # type: ignore[no-untyped-def]
    auth_cookies: dict[str, str],
) -> None:
    """Start impossível → 400 `invalid_start_date`."""
    response = client.post(
        "/calendar/events",
        json={"summary": "Teste", "start": "zxxy bla", "end": ""},
        cookies=auth_cookies,
    )
    assert response.status_code == 400
    assert "invalid_start_date" in response.json()["detail"]


def test_update_event_normalizes_start(
    client,  # type: ignore[no-untyped-def]
    mocker: MockerFixture,
    auth_cookies: dict[str, str],
) -> None:
    """PATCH também normaliza PT → ISO."""
    mock_update = mocker.patch(
        "app.services.calendar.update_event",
        return_value=_fake_event(),
    )
    response = client.patch(
        "/calendar/events/abc123",
        json={"start": "amanhã às 10h"},
        cookies=auth_cookies,
    )
    assert response.status_code in (200, 201), response.text
    kwargs = mock_update.call_args.kwargs
    from datetime import datetime

    assert datetime.fromisoformat(kwargs["start"]).hour == 10


def test_update_event_rejects_unparseable_start(
    client,  # type: ignore[no-untyped-def]
    auth_cookies: dict[str, str],
) -> None:
    response = client.patch(
        "/calendar/events/abc123",
        json={"start": "zxxy"},
        cookies=auth_cookies,
    )
    assert response.status_code == 400
    assert "invalid_start_date" in response.json()["detail"]
