"""Google Calendar v3 API wrapper for Vox agent.

Exposes:
    - list_events(user_id, time_min, time_max, max_results) — upcoming events
    - get_event(user_id, event_id) — single event detail
    - create_event(user_id, summary, start, end, description, location) — create event
    - update_event(user_id, event_id, **fields) — patch event
    - delete_event(user_id, event_id) — delete event

Reuses credential management from gmail._get_valid_credentials.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient import discovery

from app.config import get_settings
from app.logging import get_logger
from app.services.gmail import _decode_bytea, _encode_bytea, _select_primary_account
from app.services import crypto, supabase_client

logger = get_logger(__name__)

_TOKEN_URI = "https://oauth2.googleapis.com/token"
_DEFAULT_MAX_RESULTS = 25


def _get_valid_credentials(user_id: str) -> Credentials:
    """Build valid Google credentials with refresh — mirrors gmail pattern."""
    settings = get_settings()
    sb = supabase_client.get_supabase_admin()

    rows: list[dict[str, Any]] = (
        sb.table("google_accounts").select("*").eq("user_id", user_id).execute().data
    )
    row = _select_primary_account(rows)

    refresh_token = _decode_bytea(row["refresh_token_encrypted"])
    refresh_plaintext = crypto.decrypt(refresh_token).decode("utf-8")

    access_plaintext: str | None = None
    access_cipher = row.get("access_token_encrypted")
    if access_cipher:
        access_bytes = _decode_bytea(access_cipher)
        access_plaintext = crypto.decrypt(access_bytes).decode("utf-8")

    credentials = Credentials(
        token=access_plaintext,
        refresh_token=refresh_plaintext,
        token_uri=_TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=row.get("scopes") or [],
    )

    if credentials.expired:
        credentials.refresh(Request())
        logger.info("calendar.credentials.refreshed", account_id=row.get("id"))
        new_token = credentials.token
        if new_token:
            new_expiry = getattr(credentials, "expiry", None)
            if new_expiry is None:
                new_expiry_iso = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
            else:
                if new_expiry.tzinfo is None:
                    new_expiry_iso = new_expiry.replace(tzinfo=UTC).isoformat()
                else:
                    new_expiry_iso = new_expiry.isoformat()
            new_cipher = crypto.encrypt(new_token.encode("utf-8"))
            sb.table("google_accounts").update(
                {
                    "access_token_encrypted": _encode_bytea(new_cipher),
                    "access_token_expires_at": new_expiry_iso,
                }
            ).eq("id", row["id"]).execute()

    return credentials


def _parse_event(event: dict[str, Any]) -> dict[str, Any]:
    """Extract relevant fields from a Calendar API event resource."""
    start = event.get("start", {}) or {}
    end = event.get("end", {}) or {}

    start_dt = start.get("dateTime", start.get("date", ""))
    end_dt = end.get("dateTime", end.get("date", ""))
    is_all_day = "date" in start and "dateTime" not in start

    attendees = []
    for att in event.get("attendees", []) or []:
        attendees.append(
            {
                "email": att.get("email", ""),
                "name": att.get("displayName", ""),
                "response_status": att.get("responseStatus", ""),
            }
        )

    return {
        "id": event.get("id", ""),
        "summary": event.get("summary", ""),
        "description": event.get("description", "") or "",
        "location": event.get("location", "") or "",
        "start": start_dt,
        "end": end_dt,
        "is_all_day": is_all_day,
        "attendees": attendees,
        "status": event.get("status", ""),
        "html_link": event.get("htmlLink", ""),
    }


def list_events(
    user_id: str,
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = _DEFAULT_MAX_RESULTS,
) -> dict[str, Any]:
    """List upcoming calendar events.

    Args:
        user_id: UUID of the user.
        time_min: ISO 8601 lower bound (default: now).
        time_max: ISO 8601 upper bound (default: 7 days from now).
        max_results: Maximum events to return.

    Returns:
        {"events": [...], "count": int}
    """
    creds = _get_valid_credentials(user_id)
    service = discovery.build("calendar", "v3", credentials=creds, cache_discovery=False)

    if not time_min:
        time_min = datetime.now(UTC).isoformat()
    if not time_max:
        time_max = (datetime.now(UTC) + timedelta(days=7)).isoformat()

    events_result: dict[str, Any] = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    items = events_result.get("items", []) or []
    events = [_parse_event(e) for e in items]

    logger.info("calendar.list", event_count=len(events))
    return {"events": events, "count": len(events)}


def get_event(user_id: str, event_id: str) -> dict[str, Any]:
    """Get a single calendar event by ID."""
    creds = _get_valid_credentials(user_id)
    service = discovery.build("calendar", "v3", credentials=creds, cache_discovery=False)

    event: dict[str, Any] = service.events().get(calendarId="primary", eventId=event_id).execute()

    logger.info("calendar.get", event_id=event_id)
    return _parse_event(event)


def create_event(
    user_id: str,
    summary: str,
    start: str,
    end: str,
    description: str = "",
    location: str = "",
) -> dict[str, Any]:
    """Create a new calendar event.

    Args:
        user_id: UUID of the user.
        summary: Event title.
        start: ISO 8601 datetime or date string.
        end: ISO 8601 datetime or date string.
        description: Optional description.
        location: Optional location.

    Returns:
        Parsed event dict.
    """
    creds = _get_valid_credentials(user_id)
    service = discovery.build("calendar", "v3", credentials=creds, cache_discovery=False)

    is_all_day = "T" not in start
    if is_all_day:
        event_body: dict[str, Any] = {
            "summary": summary,
            "start": {"date": start[:10]},
            "end": {"date": end[:10]},
        }
    else:
        event_body = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": "Europe/Lisbon"},
            "end": {"dateTime": end, "timeZone": "Europe/Lisbon"},
        }

    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location

    created: dict[str, Any] = (
        service.events().insert(calendarId="primary", body=event_body).execute()
    )

    logger.info("calendar.create", event_id=created.get("id", ""))
    return _parse_event(created)


def update_event(
    user_id: str,
    event_id: str,
    **fields: Any,
) -> dict[str, Any]:
    """Patch an existing calendar event.

    Args:
        user_id: UUID of the user.
        event_id: Calendar event ID.
        **fields: Fields to update (summary, description, location, start, end).

    Returns:
        Updated parsed event dict.
    """
    creds = _get_valid_credentials(user_id)
    service = discovery.build("calendar", "v3", credentials=creds, cache_discovery=False)

    event_body: dict[str, Any] = {}

    if "summary" in fields:
        event_body["summary"] = fields["summary"]
    if "description" in fields:
        event_body["description"] = fields["description"]
    if "location" in fields:
        event_body["location"] = fields["location"]
    if "start" in fields:
        s = fields["start"]
        if "T" in s:
            event_body["start"] = {"dateTime": s, "timeZone": "Europe/Lisbon"}
        else:
            event_body["start"] = {"date": s[:10]}
    if "end" in fields:
        e = fields["end"]
        if "T" in e:
            event_body["end"] = {"dateTime": e, "timeZone": "Europe/Lisbon"}
        else:
            event_body["end"] = {"date": e[:10]}

    updated: dict[str, Any] = (
        service.events().patch(calendarId="primary", eventId=event_id, body=event_body).execute()
    )

    logger.info("calendar.update", event_id=event_id)
    return _parse_event(updated)


def delete_event(user_id: str, event_id: str) -> dict[str, str]:
    """Delete a calendar event.

    Returns:
        {"status": "deleted", "event_id": str}
    """
    creds = _get_valid_credentials(user_id)
    service = discovery.build("calendar", "v3", credentials=creds, cache_discovery=False)

    service.events().delete(calendarId="primary", eventId=event_id).execute()

    logger.info("calendar.delete", event_id=event_id)
    return {"status": "deleted", "event_id": event_id}
