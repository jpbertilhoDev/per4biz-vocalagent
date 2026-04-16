"""
Helpers HTTP para o fluxo OAuth 2.0 da Google (SPEC §4.1 passos 5-6).

Exponibiliza duas funções sync (compatíveis com `TestClient` sync):

    - `exchange_code_for_tokens(code)` — POST https://oauth2.googleapis.com/token
    - `fetch_userinfo(access_token)`   — GET  https://www.googleapis.com/oauth2/v2/userinfo

Nenhuma função loga `code`, tokens, userinfo completo ou response bodies.
Apenas `status_code` e identificadores anonimizados (sub/email é tratado como
PII e NÃO é logado — LOGGING-POLICY).
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)

_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 — URL pública, não secret
_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
_REVOKE_URL = "https://oauth2.googleapis.com/revoke"  # noqa: S105 — URL pública, não secret
_HTTP_TIMEOUT = 10.0


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Troca `code` por tokens via Google OAuth token endpoint.

    Args:
        code: `authorization_code` recebido no callback `/auth/google/callback`.

    Returns:
        Dicionário com pelo menos `access_token`, `refresh_token`, `id_token`,
        `expires_in`, `token_type` e `scope` (ver SPEC §4.1 passo 5).

    Raises:
        httpx.HTTPStatusError: se o Google responder com 4xx/5xx.
    """
    settings = get_settings()
    payload = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    with httpx.Client(timeout=_HTTP_TIMEOUT) as http:
        response = http.post(_TOKEN_URL, data=payload)
    logger.info("google_oauth.token_exchange", status_code=response.status_code)
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def fetch_userinfo(access_token: str) -> dict[str, Any]:
    """Obtém o perfil básico do utilizador via Google Userinfo v2.

    Args:
        access_token: token Bearer retornado por `exchange_code_for_tokens`.

    Returns:
        Dicionário com `sub`, `email`, `email_verified`, `name`, `picture`, ...
        (ver SPEC §4.1 passo 6).

    Raises:
        httpx.HTTPStatusError: se o Google responder com 4xx/5xx.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=_HTTP_TIMEOUT) as http:
        response = http.get(_USERINFO_URL, headers=headers)
    logger.info("google_oauth.userinfo", status_code=response.status_code)
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def revoke_token(refresh_token: str) -> None:
    """Revoga `refresh_token` junto do Google (RFC 7009).

    SPEC §3 RF-1.4 + AC-5 — chamado pelo `DELETE /me` para invalidar tokens
    externamente antes do cascade delete em Supabase. Best-effort:

        - 200 → revogado com sucesso.
        - 400 → token já inválido/expirado (semanticamente OK em erasure).
        - Outro status / erro de rede → warning logado, função retorna
          normalmente. O erasure prossegue mesmo que o Google esteja
          indisponível (nunca bloquear GDPR Art. 17 por falha externa).

    Invariante LOGGING-POLICY:
        NUNCA loga `refresh_token` (nem fragmento, nem hash). Apenas
        `status_code` / `error_type`.
    """
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as http:
            response = http.post(
                _REVOKE_URL,
                data={"token": refresh_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as exc:
        logger.warning(
            "google_oauth.revoke.http_error",
            error_type=type(exc).__name__,
        )
        return

    if response.status_code in (200, 400):
        logger.info("google_oauth.revoke", status_code=response.status_code)
    else:
        logger.warning(
            "google_oauth.revoke.unexpected_status",
            status_code=response.status_code,
        )
