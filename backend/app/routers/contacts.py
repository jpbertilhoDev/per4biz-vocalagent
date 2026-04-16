"""Router `/contacts` — Google People API contacts (Sprint 4 · Full Agent).

Endpoints:
    - GET  /contacts/search?query=... → search contacts
    - GET  /contacts/list             → list recent contacts

All endpoints require `__Host-session` cookie (via `current_user` dep).
RefreshError handling: cleans up google_accounts + clears session cookie.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.auth.exceptions import RefreshError

from app.deps import current_user
from app.logging import get_logger
from app.services import contacts
from app.services.auth_helpers import invalid_grant_response

logger = get_logger(__name__)

router = APIRouter(prefix="/contacts", tags=["contacts"])

_CurrentUser = Depends(current_user)


@router.get("/search")
def search_contacts(
    query: str = Query(..., min_length=1, max_length=200),
    max_results: int = Query(20, ge=1, le=100),
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """Search contacts by name or email."""
    try:
        result = contacts.search_contacts(
            user["sub"],
            query=query,
            max_results=max_results,
        )
    except RefreshError:
        return invalid_grant_response(user["sub"])
    except LookupError:
        return invalid_grant_response(user["sub"])
    except Exception as exc:
        logger.warning("contacts.search.failed", error_type=type(exc).__name__)
        raise HTTPException(status_code=502, detail="contacts upstream error") from exc
    return result


@router.get("/list")
def list_contacts(
    max_results: int = Query(20, ge=1, le=100),
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """List recent contacts."""
    try:
        result = contacts.list_contacts(
            user["sub"],
            max_results=max_results,
        )
    except RefreshError:
        return invalid_grant_response(user["sub"])
    except LookupError:
        return invalid_grant_response(user["sub"])
    except Exception as exc:
        logger.warning("contacts.list.failed", error_type=type(exc).__name__)
        raise HTTPException(status_code=502, detail="contacts upstream error") from exc
    return result
