"""Tests para app.services.telemetry (E10 Phase 1)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services import telemetry


@pytest.fixture
def mock_supabase():
    with patch("app.services.telemetry.get_supabase_client") as m:
        client = MagicMock()
        m.return_value = client
        yield client


def test_emit_phase_writes_row(mock_supabase):
    session_id = uuid4()
    telemetry.emit_phase(
        session_id=session_id,
        user_id="00000000-0000-0000-0000-000000000000",
        phase="stt_done",
        ms=412,
        status="ok",
    )

    mock_supabase.table.assert_called_once_with("voice_latency_events")
    insert_args = mock_supabase.table.return_value.insert.call_args[0][0]
    assert insert_args["voice_session_id"] == str(session_id)
    assert insert_args["phase"] == "stt_done"
    assert insert_args["ms"] == 412
    assert insert_args["status"] == "ok"
    mock_supabase.table.return_value.insert.return_value.execute.assert_called_once()


def test_emit_phase_rejects_negative_ms(mock_supabase):
    with pytest.raises(ValueError, match="ms must be >= 0"):
        telemetry.emit_phase(
            session_id=uuid4(),
            user_id="u",
            phase="p",
            ms=-1,
            status="ok",
        )
    mock_supabase.table.assert_not_called()


def test_emit_phase_swallows_supabase_errors(mock_supabase):
    """Telemetry must never break the voice pipeline."""
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError("db down")

    # Should not raise
    telemetry.emit_phase(
        session_id=uuid4(),
        user_id="u",
        phase="stt_done",
        ms=100,
        status="ok",
    )
