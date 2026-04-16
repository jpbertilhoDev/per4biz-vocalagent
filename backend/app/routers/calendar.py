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

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field

from app.deps import current_user
from app.logging import get_logger
from app.services import calendar
from app.services.auth_helpers import invalid_grant_response

logger = get_logger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])

_CurrentUser = Depends(current_user)


def _handle_google_http_error(exc: HttpError, operation: str) -> None:
    """Translate Google API HttpError into appropriate HTTP responses.

    - 403 Insufficient Permission → 403 with re-auth hint
    - 403 Calendar API not enabled → 502 with specific detail
    - 404 Not Found → 404
    - Other → 502
    """
    resp_status = exc.resp.status if exc.resp else 500
    error_content = str(exc.content or b"").lower() if exc.content else ""

    logger.warning(
        f"calendar.{operation}.google_error",
        status_code=resp_status,
        error_type=type(exc).__name__,
        error_reason=str(exc)[:200],
    )

    if resp_status == 403:
        if "insufficient permission" in error_content or "insufficientpermissions" in error_content:
            raise HTTPException(
                status_code=403,
                detail="calendar_scope_missing",
            ) from exc
        if "has not been used" in error_content or "not been enabled" in error_content:
            raise HTTPException(
                status_code=502,
                detail="calendar_api_not_enabled",
            ) from exc
    if resp_status == 404:
        raise HTTPException(status_code=404, detail="calendar event not found") from exc

    raise HTTPException(status_code=502, detail="calendar upstream error") from exc


class CreateEventRequest(BaseModel):
    summary: str = Field(..., min_length=1, max_length=500)
    start: str = Field(..., min_length=1)
    end: str = Field(..., min_length=1)
    description: str = ""
    location: str = ""


class UpdateEventRequest(BaseModel):
    summary: str | None = None
    start: str | None = None
    end: str | None = None
    description: str | None = None
    location: str | None = None


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
    """Create a new calendar event."""
    try:
        result = calendar.create_event(
            user["sub"],
            summary=req.summary,
            start=req.start,
            end=req.end,
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
        fields["start"] = req.start
    if req.end is not None:
        fields["end"] = req.end
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
