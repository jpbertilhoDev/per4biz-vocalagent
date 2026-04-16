"""
Router do fluxo OAuth Google (Sprint 1 · E1 · SPEC §4.1).

Endpoints:
    - GET  /auth/google/start     → redirect 307 para consent Google (R-E1.5: prompt=consent)
    - GET  /auth/google/callback  → troca code→tokens, valida gating, cifra tokens,
                                    persiste em Supabase, emite cookie de sessão.

Invariantes de segurança (CLAUDE.md §3, SPEC §5):
    - Gating `ALLOWED_USER_EMAIL` executado ANTES de qualquer escrita em Supabase.
    - Tokens cifrados AES-256-GCM (bytes) — ver `app.services.crypto`.
    - Cookie `__Host-session` (Secure + Path=/ + sem Domain) OBRIGATÓRIO.
    - Zero logs de `code`, tokens, id_token, state cru ou bodies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from jose import ExpiredSignatureError, JWTError

from app.config import get_settings
from app.logging import get_logger
from app.services import crypto, google_oauth, supabase_client
from app.services.session_jwt import issue_session
from app.services.state_jwt import sign_state, verify_state

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_SCOPES = " ".join(
    [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/contacts.readonly",
    ]
)
_SESSION_COOKIE_NAME = "__Host-session"
_SESSION_MAX_AGE_SECONDS = 7 * 86400
_CONSENT_POLICY_TYPE = "privacy"
_CONSENT_POLICY_VERSION = "privacy-v1.0"


@router.get("/auth/google/start")
def start() -> RedirectResponse:
    """Inicia o fluxo OAuth Google (SPEC §4.1 passo 3).

    Gera o state JWT (CSRF, TTL 10min) e redireciona o utilizador para o
    consent screen do Google com `access_type=offline` + `prompt=consent`
    para forçar a emissão de refresh_token (R-E1.5).
    """
    settings = get_settings()
    state = sign_state(redirect_to="/chat")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": _GOOGLE_SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(
        url=f"{_GOOGLE_AUTH_URL}?{urlencode(params)}",
        status_code=307,
    )


@router.get("/auth/google/callback")
def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Processa o callback OAuth (SPEC §4.1 passos 4-7).

    Sequência:
        1. Se `?error=…` → redirect home sem tocar Supabase (AC-2 cancel).
        2. Valida `state` (CSRF · AC-7).
        3. Troca `code` por tokens + busca userinfo.
        4. Gating `ALLOWED_USER_EMAIL` (CLAUDE.md §3 regra 8).
        5. Cifra access/refresh tokens (AES-256-GCM).
        6. Upsert `users` + `google_accounts`; insert `consent_log`.
        7. Emite cookie `__Host-session` e redireciona para `redirect_to`.
    """
    settings = get_settings()

    # 1. Cancel / consent screen error — redirect home sem tocar Supabase
    if error:
        logger.info("auth.callback.cancel", error_code=error)
        return RedirectResponse(url="/", status_code=307)

    # 2. Validar state (CSRF · AC-7)
    if not state:
        raise HTTPException(status_code=400, detail="Invalid state")
    try:
        state_payload = verify_state(state)
    except (ExpiredSignatureError, JWTError) as exc:
        logger.warning("auth.callback.invalid_state", reason=type(exc).__name__)
        raise HTTPException(status_code=400, detail="Invalid state") from exc

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # 3. Trocar code por tokens + userinfo
    tokens = google_oauth.exchange_code_for_tokens(code)
    userinfo = google_oauth.fetch_userinfo(tokens["access_token"])

    # 4. Gating ALLOWED_USER_EMAIL — ANTES de qualquer escrita em Supabase
    if userinfo.get("email") != settings.ALLOWED_USER_EMAIL:
        logger.warning("auth.callback.email_not_allowed")
        raise HTTPException(status_code=403, detail="Email not allowed")

    # 5. Cifrar tokens (AES-256-GCM) — bytes
    refresh_encrypted = crypto.encrypt(tokens["refresh_token"].encode("utf-8"))
    access_encrypted = crypto.encrypt(tokens["access_token"].encode("utf-8"))
    expires_in = int(tokens.get("expires_in", 3600))
    access_expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()
    scopes_raw = tokens.get("scope", "")
    scopes_list = scopes_raw.split(" ") if scopes_raw else []

    # 6. Persistir em Supabase (users → google_accounts → consent_log)
    sb = supabase_client.get_supabase_admin()

    user_payload: dict[str, Any] = {
        "id": settings.USER_ID,
        "email": userinfo["email"],
        "full_name": userinfo.get("name"),
    }
    sb.table("users").upsert(user_payload).execute()

    google_account_payload: dict[str, Any] = {
        "user_id": settings.USER_ID,
        "google_email": userinfo["email"],
        "refresh_token_encrypted": f"\\x{refresh_encrypted.hex()}",
        "access_token_encrypted": f"\\x{access_encrypted.hex()}",
        "access_token_expires_at": access_expires_at,
        "scopes": scopes_list,
        "is_primary": True,
        "key_version": settings.ENCRYPTION_KEY_VERSION,
    }
    sb.table("google_accounts").upsert(
        google_account_payload,
        on_conflict="user_id,google_email",
    ).execute()

    consent_payload: dict[str, Any] = {
        "user_id": settings.USER_ID,
        "policy_type": _CONSENT_POLICY_TYPE,
        "policy_version": _CONSENT_POLICY_VERSION,
        "consent_given": True,
    }
    sb.table("consent_log").insert(consent_payload).execute()

    logger.info("auth.callback.success")

    # 7. Emitir session JWT + cookie `__Host-session`
    session_token = issue_session(UUID(settings.USER_ID), userinfo["email"])
    redirect_path = state_payload.get("redirect_to") or "/inbox"
    # Redirect para o frontend (origem diferente do backend)
    redirect_url = f"{settings.NEXT_PUBLIC_APP_URL.rstrip('/')}{redirect_path}"

    response = RedirectResponse(url=redirect_url, status_code=307)
    response.set_cookie(
        key=_SESSION_COOKIE_NAME,
        value=session_token,
        max_age=_SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return response
