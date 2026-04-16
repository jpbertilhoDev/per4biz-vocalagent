"""Router `/calendar` — Google Calendar events (Sprint 4 · Full Agent).

Endpoints:
    - GET  /calendar/events           → list upcoming events
    - GET  /calendar/events/{event_id} → get event detail
    - POST /calendar/events           → create event
    - PATCH /calendar/events/{event_id} → update event
    - DELETE /calendar/events/{event_id} → delete event

All endpoints require `__Host-session` cookie (via `current_user` dep).
RefreshError handling: cleans up google_accounts + clears session cookie
(same pattern as emails.py — AC-2.7).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field

from app.deps import current_user
from app.logging import get_logger
from app.services import calendar
from app.services.auth_helpers import invalid_grant_response
from app.services.date_parser import parse_pt_datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])

_CurrentUser = Depends(current_user)


def _handle_google_http_error(exc: HttpError, operation: str) -> None:
    """Translate Google API HttpError into appropriate HTTP responses.

    - 403 Insufficient Permission → 403 with re-auth hint
    - 403 Calendar API not enabled → 502 with specific detail
    - 404 Not Found → 404
    - Other → 502 with the original Google error message exposed
    """
    resp_status = exc.resp.status if exc.resp else 500
    raw_content = exc.content.decode("utf-8", errors="replace") if exc.content else ""
    error_content_lower = raw_content.lower()

    logger.warning(
        f"calendar.{operation}.google_error",
        status_code=resp_status,
        error_type=type(exc).__name__,
        error_reason=raw_content[:500],
    )

    if resp_status == 403:
        if "insufficient permission" in error_content_lower or "insufficientpermissions" in error_content_lower:
            raise HTTPException(
                status_code=403,
                detail="calendar_scope_missing",
            ) from exc
        if "has not been used" in error_content_lower or "not been enabled" in error_content_lower or "accessnotconfigured" in error_content_lower:
            raise HTTPException(
                status_code=502,
                detail="calendar_api_not_enabled",
            ) from exc
        # Other 403 — surface the actual Google error message so the user sees it
        raise HTTPException(
            status_code=403,
            detail=f"calendar_forbidden: {raw_content[:200]}",
        ) from exc
    if resp_status == 404:
        raise HTTPException(status_code=404, detail="calendar event not found") from exc

    # Unknown error — expose the Google reason so we can debug from the UI
    raise HTTPException(
        status_code=502,
        detail=f"calendar_upstream: {raw_content[:200]}",
    ) from exc


class CreateEventRequest(BaseModel):
    summary: str = Field(..., min_length=1, max_length=500)
    start: str = Field(..., min_length=1)
    # `end` is optional at API-layer: when empty/omitted or unparseable, the
    # handler falls back to `start + 1h`. This makes the endpoint robust to
    # LLM output that forgets to emit an end time.
    end: str = ""
    description: str = ""
    location: str = ""


class UpdateEventRequest(BaseModel):
    summary: str | None = None
    start: str | None = None
    end: str | None = None
    description: str | None = None
    location: str | None = None


@router.get("/_debug/scopes")
def debug_scopes(user: dict[str, Any] = _CurrentUser) -> dict[str, Any]:
    """Diagnostic — returns the actual Google OAuth scopes stored for the user.

    Use to confirm whether re-auth granted Calendar/Contacts scopes.
    """
    from app.services import supabase_client

    sb = supabase_client.get_supabase_admin()
    rows = sb.table("google_accounts").select("google_email,scopes,is_primary,updated_at").eq("user_id", user["sub"]).execute().data
    required = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/contacts.readonly",
    ]
    accounts_summary = []
    for row in rows or []:
        scopes = row.get("scopes") or []
        accounts_summary.append({
            "google_email": row.get("google_email"),
            "is_primary": row.get("is_primary"),
            "updated_at": row.get("updated_at"),
            "scopes": scopes,
            "has_calendar": "https://www.googleapis.com/auth/calendar" in scopes,
            "has_calendar_events": "https://www.googleapis.com/auth/calendar.events" in scopes,
            "has_contacts": "https://www.googleapis.com/auth/contacts.readonly" in scopes,
            "missing_required": [s for s in required if s not in scopes],
        })
    return {"accounts": accounts_summary, "user_sub": user["sub"]}


@router.get("/events")
def list_calendar_events(
    time_min: str | None = Query(None),
    time_max: str | None = Query(None),
    max_results: int = Query(25, ge=1, le=100),
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """List upcoming calendar events for the authenticated user."""
    try:
        result = calendar.list_events(
            user["sub"],
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
        )
    except RefreshError:
        return invalid_grant_response(user["sub"])
    except LookupError:
        return invalid_grant_response(user["sub"])
    except HttpError as exc:
        _handle_google_http_error(exc, "list")
    except Exception as exc:
        logger.warning(
            "calendar.list.failed",
            error_type=type(exc).__name__,
            error_detail=str(exc)[:200],
        )
        raise HTTPException(status_code=502, detail="calendar upstream error") from exc
    return result


@router.get("/events/{event_id}")
def get_calendar_event(
    event_id: str,
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """Get a single calendar event by ID."""
    try:
        result = calendar.get_event(user["sub"], event_id)
    except RefreshError:
        return invalid_grant_response(user["sub"])
    except LookupError:
        return invalid_grant_response(user["sub"])
    except HttpError as exc:
        _handle_google_http_error(exc, "get")
    except Exception as exc:
        logger.warning(
            "calendar.get.failed",
            error_type=type(exc).__name__,
            error_detail=str(exc)[:200],
        )
        raise HTTPException(status_code=502, detail="calendar upstream error") from exc
    return result


@router.post("/events")
def create_calendar_event(
    req: CreateEventRequest,
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """Create a new calendar event.

    Safety net: normalize PT natural-language dates ("amanhã às 10h",
    "próxima quinta") to ISO 8601 before forwarding to Google. The LLM
    upstream sometimes drifts and sends raw PT strings.
    """
    start_parsed = parse_pt_datetime(req.start)
    if start_parsed is None:
        raise HTTPException(
            status_code=400,
            detail=f"invalid_start_date: {req.start!r}",
        )
    end_parsed = parse_pt_datetime(req.end) if req.end else None
    if end_parsed is None:
        # Fallback: end = start + 1h (default meeting length)
        end_parsed = start_parsed + timedelta(hours=1)

    start_iso = start_parsed.isoformat()
    end_iso = end_parsed.isoformat()

    try:
        result = calendar.create_event(
            user["sub"],
            summary=req.summary,
            start=start_iso,
            end=end_iso,
            description=req.description,
            location=req.location,
        )
    except RefreshError:
        return invalid_grant_response(user["sub"])
    except LookupError:
        return invalid_grant_response(user["sub"])
    except HttpError as exc:
        _handle_google_http_error(exc, "create")
    except Exception as exc:
        logger.warning(
            "calendar.create.failed",
            error_type=type(exc).__name__,
            error_detail=str(exc)[:200],
        )
        raise HTTPException(status_code=502, detail="calendar upstream error") from exc
    return result


@router.patch("/events/{event_id}")
def update_calendar_event(
    event_id: str,
    req: UpdateEventRequest,
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """Patch an existing calendar event."""
    fields: dict[str, Any] = {}
    if req.summary is not None:
        fields["summary"] = req.summary
    if req.start is not None:
        start_parsed = parse_pt_datetime(req.start)
        if start_parsed is None:
            raise HTTPException(
                status_code=400,
                detail=f"invalid_start_date: {req.start!r}",
            )
        fields["start"] = start_parsed.isoformat()
    if req.end is not None:
        end_parsed = parse_pt_datetime(req.end)
        if end_parsed is None:
            raise HTTPException(
                status_code=400,
                detail=f"invalid_end_date: {req.end!r}",
            )
        fields["end"] = end_parsed.isoformat()
    if req.description is not None:
        fields["description"] = req.description
    if req.location is not None:
        fields["location"] = req.location

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        result = calendar.update_event(user["sub"], event_id, **fields)
    except RefreshError:
        return invalid_grant_response(user["sub"])
    except LookupError:
        return invalid_grant_response(user["sub"])
    except HttpError as exc:
        _handle_google_http_error(exc, "update")
    except Exception as exc:
        logger.warning(
            "calendar.update.failed",
            error_type=type(exc).__name__,
            error_detail=str(exc)[:200],
        )
        raise HTTPException(status_code=502, detail="calendar upstream error") from exc
    return result


@router.delete("/events/{event_id}")
def delete_calendar_event(
    event_id: str,
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """Delete a calendar event."""
    try:
        result = calendar.delete_event(user["sub"], event_id)
    except RefreshError:
        return invalid_grant_response(user["sub"])
    except LookupError:
        return invalid_grant_response(user["sub"])
    except HttpError as exc:
        _handle_google_http_error(exc, "delete")
    except Exception as exc:
        logger.warning(
            "calendar.delete.failed",
            error_type=type(exc).__name__,
            error_detail=str(exc)[:200],
        )
        raise HTTPException(status_code=502, detail="calendar upstream error") from exc
    return result
