"""Shared invalid-grant handler for Google API routers.

Extracted from emails.py to be reused by calendar + contacts routers.
Handles RefreshError (revoked token) by cleaning up google_accounts
and clearing the session cookie, forcing re-authentication.
"""

from __future__ import annotations

from fastapi import status
from fastapi.responses import JSONResponse, Response

from app.logging import get_logger
from app.middleware.session import SESSION_COOKIE
from app.services import supabase_client

logger = get_logger(__name__)


def invalid_grant_response(user_sub: str) -> Response:
    """AC-2.7: apaga `google_accounts`, devolve 401 e invalida cookie.

    Usamos `JSONResponse` directa (em vez de `HTTPException`) porque
    precisamos de anexar `Set-Cookie __Host-session=; Max-Age=0` à mesma
    response que transporta o 401.
    """
    try:
        sb = supabase_client.get_supabase_admin()
        sb.table("google_accounts").delete().eq("user_id", user_sub).execute()
    except Exception as exc:  # noqa: BLE001 — cleanup best-effort
        logger.warning(
            "invalid_grant.cleanup_failed",
            error_type=type(exc).__name__,
        )

    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Google access revoked"},
    )
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=True,
        httponly=True,
        samesite="none",
    )
    logger.info("invalid_grant.cleanup_done")
    return response
