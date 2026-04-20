"""Tests for POST /voice/telemetry (E10 Phase 1 · Task 4).

Fire-and-forget batch endpoint that writes phase timings via
`telemetry.emit_phase`. Auth via existing `__Host-session` cookie pattern
(SessionMiddleware-based, same as other voice tests).
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from app.services.session_jwt import issue_session
from fastapi.testclient import TestClient

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
EMAIL = "test@per4biz.local"
COOKIE_NAME = "__Host-session"


@pytest.fixture
def auth_cookies() -> dict[str, str]:
    """Cookie de sessão válido — SessionMiddleware popula `current_user`."""
    token = issue_session(USER_ID, EMAIL)
    return {COOKIE_NAME: token}


def test_voice_telemetry_accepts_batch(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    session_id = uuid4()
    payload = {
        "events": [
            {"phase": "vad_cut", "ms": 512, "status": "ok"},
            {"phase": "stt_done", "ms": 880, "status": "ok"},
        ]
    }
    with patch("app.routers.voice.telemetry.emit_phase") as emit:
        resp = client.post(
            "/voice/telemetry",
            json=payload,
            headers={"X-Voice-Session-Id": str(session_id)},
            cookies=auth_cookies,
        )
    assert resp.status_code == 204, (
        f"esperado 204, recebido {resp.status_code} (body: {resp.text[:200]})"
    )
    assert emit.call_count == 2, (
        f"esperado 2 chamadas a emit_phase, recebidas {emit.call_count}"
    )
    # Verifica que session_id + user_id canónicos são propagados
    call_kwargs = emit.call_args_list[0].kwargs
    assert call_kwargs["session_id"] == session_id
    assert call_kwargs["user_id"] == str(USER_ID)
    assert call_kwargs["phase"] == "vad_cut"


def test_voice_telemetry_missing_session_id_returns_400(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    """Sem header `X-Voice-Session-Id` → 400 (não 422 — endpoint-specific check)."""
    resp = client.post(
        "/voice/telemetry",
        json={"events": []},
        cookies=auth_cookies,
    )
    assert resp.status_code == 400, (
        f"esperado 400, recebido {resp.status_code} (body: {resp.text[:200]})"
    )
