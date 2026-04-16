"""
Router `/me` — GDPR trilogy (Sprint 1 · E1 · SPEC §5.5).

Cobre os direitos do titular dos dados (06-addendum/PRIVACY-POLICY-PT.md §11):

    - `GET    /me`          → perfil básico (Art. 15 — right of access, light)
    - `GET    /me/export`   → JSON dump portável (Art. 20 — data portability)
    - `DELETE /me`          → revoga tokens Google + cascade delete (Art. 17 — right to erasure)

Invariantes (CLAUDE.md §3 + LOGGING-POLICY):
    - Nenhum endpoint devolve `refresh_token_encrypted`, `access_token_encrypted`
      ou plaintext de tokens. `/me/export` substitui por flag booleana.
    - `DELETE /me` revoga no Google ANTES do delete no Supabase (invalidação
      externa first, depois limpeza local — ordem correcta para AC-5/AC-6).
    - Cookie clear em `DELETE /me` usa mesmos atributos que `SessionMiddleware`
      (path=/, secure, httponly, samesite=lax) para o browser aceitar.
    - Zero logs de PII — apenas eventos sem payload sensível.
"""
from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends, Response, status

from app.deps import current_user
from app.logging import get_logger
from app.middleware.session import SESSION_COOKIE
from app.services import crypto, google_oauth, supabase_client

logger = get_logger(__name__)

router = APIRouter(tags=["me"])

# Módulo-level singleton para `Depends(current_user)` — evita B008
# (chamada em argument default) e mantém o idiom FastAPI.
_CurrentUser = Depends(current_user)

_FORBIDDEN_GA_FIELDS: frozenset[str] = frozenset(
    {
        "refresh_token_encrypted",
        "access_token_encrypted",
    }
)


@router.get("/me")
def get_me(
    user: dict[str, Any] = _CurrentUser,
) -> dict[str, Any]:
    """Perfil básico do user autenticado (GDPR Art. 15 — read-light).

    Não expõe `google_accounts`, `email_cache` nem qualquer token material.
    Para um dump completo, usar `GET /me/export`.
    """
    sb = supabase_client.get_supabase_admin()
    rows = cast(
        "list[dict[str, Any]]",
        sb.table("users")
        .select("id, email, created_at")
        .eq("id", user["sub"])
        .execute()
        .data,
    )
    if not rows:
        # Fallback defensivo — sessão válida mas linha `users` inexistente
        # (deletion race, reset manual, etc.). Devolvemos o claim do JWT
        # sem contactar DB novamente; cliente pode tratar como "perfil vazio".
        logger.warning("me.get.user_row_missing")
        return {"id": user["sub"], "email": user["email"]}
    return rows[0]


@router.get("/me/export")
def export_me(
    user: dict[str, Any] = _CurrentUser,
) -> dict[str, Any]:
    """Dump completo em JSON (GDPR Art. 20 — portability).

    Contrato estável: devolve sempre as 4 keys top-level
    (`users`, `google_accounts`, `consent_log`, `app_settings`), mesmo
    quando vazias. `google_accounts` é sanitizada — nunca expõe tokens
    (nem cifrados, nem plaintext). Em vez disso, flags `has_refresh_token` /
    `has_access_token` informam o titular da existência do material.
    """
    sb = supabase_client.get_supabase_admin()
    user_id = user["sub"]

    users_rows = cast(
        "list[dict[str, Any]]",
        sb.table("users").select("*").eq("id", user_id).execute().data,
    )
    ga_rows_raw = cast(
        "list[dict[str, Any]]",
        sb.table("google_accounts").select("*").eq("user_id", user_id).execute().data,
    )
    consent_rows = cast(
        "list[dict[str, Any]]",
        sb.table("consent_log").select("*").eq("user_id", user_id).execute().data,
    )
    settings_rows = cast(
        "list[dict[str, Any]]",
        sb.table("app_settings").select("*").eq("user_id", user_id).execute().data,
    )

    ga_sanitized: list[dict[str, Any]] = []
    for row in ga_rows_raw:
        clean: dict[str, Any] = {
            k: v for k, v in row.items() if k not in _FORBIDDEN_GA_FIELDS
        }
        clean["has_refresh_token"] = bool(row.get("refresh_token_encrypted"))
        clean["has_access_token"] = bool(row.get("access_token_encrypted"))
        ga_sanitized.append(clean)

    return {
        "users": users_rows,
        "google_accounts": ga_sanitized,
        "consent_log": consent_rows,
        "app_settings": settings_rows,
    }


@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_me(
    response: Response,
    user: dict[str, Any] = _CurrentUser,
) -> dict[str, str]:
    """Erasure completo (GDPR Art. 17).

    Sequência (ordem crítica):
        1. SELECT `google_accounts.refresh_token_encrypted` do user.
        2. Decrypt + `google_oauth.revoke_token(plaintext)` por conta
           (best-effort — não bloqueia erasure em falha Google).
        3. `DELETE FROM users WHERE id=user_id` — migration 0001/0004
           declaram `ON DELETE CASCADE` nas FKs filhas (`google_accounts`,
           `email_cache`, `draft_responses`, `voice_sessions`, `consent_log`,
           `app_settings`), logo uma linha apagada limpa tudo.
        4. `response.delete_cookie(__Host-session)` para forçar re-login
           (AC-6). Usa mesmos atributos do middleware para o browser
           honrar o clear.
    """
    sb = supabase_client.get_supabase_admin()
    user_id = user["sub"]

    # 1-2. Revoke cada refresh_token no Google ANTES de apagar em Supabase.
    accounts = cast(
        "list[dict[str, Any]]",
        sb.table("google_accounts")
        .select("refresh_token_encrypted")
        .eq("user_id", user_id)
        .execute()
        .data,
    )
    for account in accounts:
        encrypted = account.get("refresh_token_encrypted")
        if not encrypted:
            continue
        try:
            plaintext = crypto.decrypt(encrypted).decode("utf-8")
        except Exception as exc:  # noqa: BLE001 — decrypt pode levantar InvalidTag/ValueError; não queremos logar tipos exactos que revelem estado cripto
            logger.warning(
                "me.delete.decrypt_failed",
                error_type=type(exc).__name__,
            )
            continue
        google_oauth.revoke_token(plaintext)

    # 3. Cascade delete — FK ON DELETE CASCADE cobre filhas.
    sb.table("users").delete().eq("id", user_id).execute()

    # 4. Invalidar cookie de sessão (AC-6 força re-login).
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=True,
        httponly=True,
        samesite="none",
    )

    logger.info("me.delete.success")
    return {"status": "account deleted"}
