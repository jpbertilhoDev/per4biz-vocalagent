"""Tests for POST /voice/telemetry (E10 Phase 1 · Task 4).

Fire-and-forget batch endpoint that writes phase timings via
`telemetry.emit_phase`. Auth via existing `__Host-session` cookie pattern
(SessionMiddleware-based, same as other voice tests).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
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


# ---------------------------------------------------------------------------
# Task 5 — phase instrumentation smoke tests
# ---------------------------------------------------------------------------


def test_voice_stt_emits_start_and_done_phases(monkeypatch: pytest.MonkeyPatch) -> None:
    """`voice_stt.transcribe(..., session_id=..., user_id=...)` emits both phases."""
    from app.services import voice_stt

    phases_seen: list[tuple[str, str]] = []

    def fake_emit(
        session_id: UUID, user_id: str, phase: str, ms: int, status: str = "ok"
    ) -> None:
        phases_seen.append((phase, status))

    monkeypatch.setattr("app.services.voice_stt.telemetry.emit_phase", fake_emit)

    class _FakeResult:
        text = "olá mundo"
        duration = 1.0
        language = "pt"

    def fake_retry(_fn, **_kwargs):  # type: ignore[no-untyped-def]
        return _FakeResult()

    monkeypatch.setattr("app.services.voice_stt.retry_with_backoff", fake_retry)
    monkeypatch.setattr(
        "app.services.voice_stt.Groq", lambda **_kw: MagicMock()
    )

    session_id = uuid4()
    result = voice_stt.transcribe(
        b"\x00\x00\x00",
        mime="audio/webm",
        session_id=session_id,
        user_id=str(USER_ID),
    )
    assert result["text"] == "olá mundo"
    assert ("stt_start", "ok") in phases_seen
    assert ("stt_done", "ok") in phases_seen


def test_voice_stt_no_session_id_skips_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without session_id/user_id, `transcribe` must not call emit_phase."""
    from app.services import voice_stt

    emit_calls: list[tuple[str, str]] = []

    def fake_emit(*_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
        emit_calls.append(("called", "x"))

    monkeypatch.setattr("app.services.voice_stt.telemetry.emit_phase", fake_emit)

    class _FakeResult:
        text = "x"
        duration = 0.0
        language = "pt"

    monkeypatch.setattr(
        "app.services.voice_stt.retry_with_backoff",
        lambda _fn, **_kw: _FakeResult(),
    )
    monkeypatch.setattr("app.services.voice_stt.Groq", lambda **_kw: MagicMock())

    voice_stt.transcribe(b"\x00", mime="audio/webm")
    assert emit_calls == [], "emit_phase must not be called when kwargs are None"


def test_voice_intent_emits_start_and_done_phases(monkeypatch: pytest.MonkeyPatch) -> None:
    """`voice_intent.classify_intent(..., session_id=..., user_id=...)` emits both phases."""
    from app.services import voice_intent

    phases_seen: list[tuple[str, str]] = []

    def fake_emit(
        session_id: UUID, user_id: str, phase: str, ms: int, status: str = "ok"
    ) -> None:
        phases_seen.append((phase, status))

    monkeypatch.setattr("app.services.voice_intent.telemetry.emit_phase", fake_emit)

    class _FakeChoice:
        class message:  # noqa: N801
            content = '{"intent":"general","params":{}}'

    class _FakeResp:
        choices = [_FakeChoice()]

    monkeypatch.setattr(
        "app.services.voice_intent.retry_with_backoff",
        lambda _fn, **_kw: _FakeResp(),
    )
    monkeypatch.setattr("app.services.voice_intent.Groq", lambda **_kw: MagicMock())

    session_id = uuid4()
    result = voice_intent.classify_intent(
        "olá",
        history=None,
        session_id=session_id,
        user_id=str(USER_ID),
    )
    assert result["intent"] == "general"
    assert ("intent_start", "ok") in phases_seen
    assert ("intent_done", "ok") in phases_seen


def test_voice_llm_chat_emits_start_and_done_phases(monkeypatch: pytest.MonkeyPatch) -> None:
    """`voice_llm.chat_response(..., session_id=..., user_id=...)` emits both phases."""
    from app.services import voice_llm

    phases_seen: list[tuple[str, str]] = []

    def fake_emit(
        session_id: UUID, user_id: str, phase: str, ms: int, status: str = "ok"
    ) -> None:
        phases_seen.append((phase, status))

    monkeypatch.setattr("app.services.voice_llm.telemetry.emit_phase", fake_emit)

    class _FakeChoice:
        class message:  # noqa: N801
            content = "Olá, tudo bem."

    class _FakeResp:
        choices = [_FakeChoice()]

    monkeypatch.setattr(
        "app.services.voice_llm.retry_with_backoff",
        lambda _fn, **_kw: _FakeResp(),
    )
    monkeypatch.setattr("app.services.voice_llm.Groq", lambda **_kw: MagicMock())

    session_id = uuid4()
    result = voice_llm.chat_response(
        "olá",
        history=None,
        session_id=session_id,
        user_id=str(USER_ID),
    )
    assert result["response_text"] == "Olá, tudo bem."
    assert ("llm_start", "ok") in phases_seen
    assert ("llm_done", "ok") in phases_seen


def test_voice_tts_emits_start_and_done_phases(monkeypatch: pytest.MonkeyPatch) -> None:
    """`voice_tts.synthesize(..., session_id=..., user_id=...)` emits both phases."""
    from app.services import voice_tts

    phases_seen: list[tuple[str, str]] = []

    def fake_emit(
        session_id: UUID, user_id: str, phase: str, ms: int, status: str = "ok"
    ) -> None:
        phases_seen.append((phase, status))

    monkeypatch.setattr("app.services.voice_tts.telemetry.emit_phase", fake_emit)
    monkeypatch.setattr(
        "app.services.voice_tts.retry_with_backoff",
        lambda _fn, **_kw: iter([b"\xff\xfb\x90\x00"]),
    )
    monkeypatch.setattr(
        "app.services.voice_tts.ElevenLabs", lambda **_kw: MagicMock()
    )

    session_id = uuid4()
    result = voice_tts.synthesize(
        "olá",
        voice_id="test-voice",
        session_id=session_id,
        user_id=str(USER_ID),
    )
    assert result["mime"] == "audio/mpeg"
    assert ("tts_start", "ok") in phases_seen
    assert ("tts_done", "ok") in phases_seen


def test_voice_tts_error_emits_done_with_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the SDK raises, the `_done` phase must be emitted with status='error'."""
    from app.services import voice_tts

    phases_seen: list[tuple[str, str]] = []

    def fake_emit(
        session_id: UUID, user_id: str, phase: str, ms: int, status: str = "ok"
    ) -> None:
        phases_seen.append((phase, status))

    monkeypatch.setattr("app.services.voice_tts.telemetry.emit_phase", fake_emit)

    def _boom(*_args, **_kw):  # type: ignore[no-untyped-def]
        raise RuntimeError("eleven down")

    monkeypatch.setattr("app.services.voice_tts.retry_with_backoff", _boom)
    monkeypatch.setattr("app.services.voice_tts.ElevenLabs", lambda **_kw: MagicMock())

    with pytest.raises(RuntimeError, match="eleven down"):
        voice_tts.synthesize(
            "olá",
            voice_id="test-voice",
            session_id=uuid4(),
            user_id=str(USER_ID),
        )

    assert ("tts_start", "ok") in phases_seen
    assert ("tts_done", "error") in phases_seen
