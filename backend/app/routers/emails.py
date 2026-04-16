"""
Router `/emails` — Gmail inbox (Sprint 1.x · E2 · SPEC §6).

Endpoints:
    - `GET /emails/list?page_token=...&limit=50` → lista paginada
      (AC-2.1 · RF-2.6).
    - `GET /emails/{message_id}` → email completo com `body_text`
      sanitizado (AC-2.2).

Tratamento de `invalid_grant` (AC-2.7 · SPEC §6):
    Se o `refresh_token` foi revogado externamente (user fez revoke em
    myaccount.google.com), `gmail._get_valid_credentials` propaga
    `google.auth.exceptions.RefreshError`. O handler:

        1. Apaga row de `google_accounts` do user (cleanup de tokens mortos).
        2. Invalida o cookie `__Host-session` (`Max-Age=0`) para forçar
           re-login no próximo request.
        3. Devolve 401 com detail neutro.

    **Não** fazemos revoke adicional no Google — o token já foi invalidado
    pelo próprio user.

Invariantes (CLAUDE.md §3 + LOGGING-POLICY):
    - Zero logs de subjects / bodies / emails. Apenas contagens e flags.
    - `current_user` dep converte ausência de cookie em 401 (AC-6).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from google.auth.exceptions import RefreshError
from pydantic import BaseModel, EmailStr, Field

from app.deps import current_user
from app.logging import get_logger
from app.middleware.session import SESSION_COOKIE
from app.services import gmail, supabase_client

logger = get_logger(__name__)

router = APIRouter(tags=["emails"])

# Módulo-level singleton para `Depends(current_user)` — evita B008
# (chamada em argument default) e mantém o idiom FastAPI.
_CurrentUser = Depends(current_user)


@router.get("/emails/list")
def list_emails(
    page_token: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """Lista até `limit` emails recentes do Gmail do user autenticado (AC-2.1)."""
    try:
        result = gmail.list_messages(user["sub"], page_token=page_token, limit=limit)
    except RefreshError:
        return _invalid_grant_response(user["sub"])
    logger.info("emails.list.success", email_count=len(result.get("emails", [])))
    return result


@router.get("/emails/{message_id}")
def get_email(
    message_id: str,
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """Retorna email completo com `body_text` HTML strippado (AC-2.2)."""
    try:
        result = gmail.get_message(user["sub"], message_id)
    except RefreshError:
        return _invalid_grant_response(user["sub"])
    logger.info("emails.get.success")
    return result


# ---------------------------------------------------------------------------
# POST /emails/send — Sprint 2 · E5 · Task 8 (RF-V.4 / RF-V.5)
# ---------------------------------------------------------------------------


class SendEmailRequest(BaseModel):
    """Payload do envio de email (SPEC §3 · RF-V.4).

    `to` é validado como ``EmailStr`` (Pydantic via ``email-validator``) —
    emails mal formados devolvem 422 antes de tocar em Gmail/Supabase
    (AC-V.7 · ERROR-MATRIX "Draft inválido").
    """

    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=998)
    body: str = Field(..., min_length=1)
    in_reply_to: str | None = None


@router.post("/emails/send")
def send_email(
    req: SendEmailRequest,
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """Envia email via Gmail + upsert `draft_responses` status=sent.

    SPEC §3 · RF-V.4 / RF-V.5 · AC-E2.US3-1 + AC-E2.US3-3.

    Flow:
        1. ``gmail.send_message(user_sub, to, subject, body, in_reply_to=...)``
           — constrói MIME RFC 5322 + chama Gmail API (ver service).
        2. Retorno ``{message_id, thread_id}`` é propagado 1:1 no JSON.
        3. Upsert em `draft_responses` com ``status='sent'`` + ``sent_at`` —
           best-effort (falha de persistência logs warning mas não bloqueia
           a response OK já que o email saiu do Gmail).

    Guardrail (CLAUDE.md §3.7): "confirmação antes de enviar" é feita
    UI-side — quando o user tapou em "Enviar" já viu o draft editável;
    este endpoint assume autorização explícita.

    Invariantes (CLAUDE.md §3 + LOGGING-POLICY):
        - Zero logs de subject/body/to — apenas IDs opacos.
    """
    try:
        result = gmail.send_message(
            user["sub"],
            req.to,
            req.subject,
            req.body,
            in_reply_to=req.in_reply_to,
        )
    except RefreshError:
        return _invalid_grant_response(user["sub"])
    except Exception as exc:  # noqa: BLE001 — Gmail API errors (quota, 5xx)
        logger.warning(
            "emails.send.upstream_failed",
            error_type=type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="gmail upstream error") from exc

    # Persist draft as sent — best-effort. Se falhar, o email já saiu;
    # não devolvemos erro ao user (o rácio correto é logar + alertar via
    # Axiom/Sentry downstream).
    try:
        sb = supabase_client.get_supabase_admin()
        account_rows = cast(
            "list[dict[str, Any]]",
            sb.table("google_accounts")
            .select("id")
            .eq("user_id", user["sub"])
            .eq("is_primary", True)
            .limit(1)
            .execute()
            .data,
        )
        if account_rows:
            sb.table("draft_responses").upsert(
                {
                    "user_id": user["sub"],
                    "google_account_id": account_rows[0]["id"],
                    "to_emails": [req.to],
                    "subject": req.subject,
                    "body_text": req.body,
                    "llm_model": "human_edited",
                    "status": "sent",
                    "sent_at": datetime.now(UTC).isoformat(),
                    "gmail_message_id_sent": result["message_id"],
                }
            ).execute()
            logger.info("emails.send.draft_persisted")
        else:
            logger.warning("emails.send.no_primary_account")
    except Exception as exc:  # noqa: BLE001 — persist failure não bloqueia 200
        logger.warning(
            "emails.send.draft_persist_failed",
            error_type=type(exc).__name__,
        )

    logger.info("emails.send.success")
    return result


def _invalid_grant_response(user_sub: str) -> Response:
    """AC-2.7: apaga `google_accounts`, devolve 401 e invalida cookie.

    Usamos `JSONResponse` directa (em vez de `HTTPException`) porque
    precisamos de anexar `Set-Cookie __Host-session=; Max-Age=0` à mesma
    response que transporta o 401. `HTTPException` descarta qualquer
    `Response` injectada via dependency e não aceita headers arbitrários
    de cookie clear.

    Cleanup do DB é best-effort — falha Supabase não deve bloquear o 401
    (o re-login seguinte recria a row correctamente).
    """
    try:
        sb = supabase_client.get_supabase_admin()
        sb.table("google_accounts").delete().eq("user_id", user_sub).execute()
    except Exception as exc:  # noqa: BLE001 — cleanup best-effort; qualquer falha Supabase não deve bloquear 401
        logger.warning(
            "emails.invalid_grant.cleanup_failed",
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
        samesite="lax",
    )
    logger.info("emails.invalid_grant.cleanup_done")
    return response
