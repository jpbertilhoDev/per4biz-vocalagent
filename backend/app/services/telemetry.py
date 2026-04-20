"""Voice telemetry service (E10 Phase 1).

Writes per-phase latency events to Supabase `voice_latency_events`.
Never raises — telemetry must not break the voice pipeline.
Zero PII per CLAUDE.md §3.3 / LOGGING-POLICY §4 — only IDs + metrics.
"""

from __future__ import annotations

from uuid import UUID

from app.logging import get_logger
from app.services.supabase_client import get_supabase_client

logger = get_logger(__name__)

_VALID_STATUSES = frozenset({"ok", "error", "timeout"})


def emit_phase(
    session_id: UUID,
    user_id: str,
    phase: str,
    ms: int,
    status: str = "ok",
) -> None:
    """Insert one row into voice_latency_events. Swallows all DB errors.

    Args:
        session_id: UUID v4 minted client-side per voice session.
        user_id: UUID of the authenticated user (hashed upstream if needed).
        phase: marker name (see spec §4 table of phases).
        ms: elapsed milliseconds since `t0 = mic stop detected`.
        status: 'ok' | 'error' | 'timeout'.
    """
    if ms < 0:
        raise ValueError("ms must be >= 0")
    if status not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}")

    try:
        client = get_supabase_client()
        client.table("voice_latency_events").insert(
            {
                "voice_session_id": str(session_id),
                "user_id": user_id,
                "phase": phase,
                "ms": ms,
                "status": status,
            }
        ).execute()
    except Exception as exc:
        # Telemetry failures must NEVER break the voice pipeline.
        logger.warning(
            "telemetry.emit_phase.failed",
            phase=phase,
            status=status,
            error_type=type(exc).__name__,
        )
