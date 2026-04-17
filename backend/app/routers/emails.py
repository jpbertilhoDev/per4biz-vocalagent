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
from fastapi.responses import Response
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from pydantic import BaseModel, EmailStr, Field

from app.deps import current_user
from app.logging import get_logger
from app.services import email_headlines, gmail, supabase_client
from app.services.auth_helpers import invalid_grant_response as _invalid_grant_response

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


# ---------------------------------------------------------------------------
# POST /emails/{message_id}/trash — Sprint V1 polish · F-Delete
# ---------------------------------------------------------------------------


class TrashResponse(BaseModel):
    """Shape devolvida por ``POST /emails/{id}/trash`` (Gmail label update).

    ``labelIds`` deverá conter ``"TRASH"`` após sucesso — o frontend usa
    isso para confirmar visualmente que a acção foi aplicada.
    """

    id: str
    labelIds: list[str] = Field(default_factory=list)  # noqa: N815 — matches Gmail API response shape (camelCase)


@router.post("/emails/{message_id}/trash", response_model=TrashResponse)
def trash_email(
    message_id: str,
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """Move um email para o lixo do Gmail (reversível · F-Delete).

    Chama ``gmail.trash_message`` → ``users.messages.trash``. O email fica
    na pasta Trash do Gmail durante 30 dias e o user pode restaurar via web
    UI. NÃO é uma delete permanente (para isso seria ``users.messages.delete``
    — intencionalmente fora de escopo V1).

    Guardrail (CLAUDE.md §3.7): destructive ops exigem confirmação explícita.
    Este endpoint assume que o frontend já mostrou a VoxCard de confirmação
    e o user tapou em "Sim, apagar" — mesma semântica do ``/emails/send``.

    Errors:
        - ``RefreshError`` → 401 + cleanup de ``google_accounts``
          (mesma lógica que outros endpoints deste router).
        - Gmail 404 → ``HTTPException(404, "email_not_found")`` — id
          inválido ou email já apagado.
        - Gmail 403 → ``HTTPException(403, "gmail_modify_scope_missing")``
          — user autorizou antes do scope ``gmail.modify`` ter sido pedido;
          frontend apresenta CTA "Autorizar".
        - Outros upstream → ``HTTPException(502, "gmail_upstream: ...")``.

    Invariantes (CLAUDE.md §3 + LOGGING-POLICY):
        - Zero logs de subject/from_email. Apenas status code + reason
          truncado + ID parcial para correlação.
    """
    try:
        result = gmail.trash_message(user["sub"], message_id)
    except RefreshError:
        return _invalid_grant_response(user["sub"])
    except HttpError as exc:
        resp_status = exc.resp.status if exc.resp else 500
        raw = exc.content.decode("utf-8", errors="replace") if exc.content else ""
        lower = raw.lower()
        if resp_status == 404:
            raise HTTPException(status_code=404, detail="email_not_found") from exc
        if resp_status == 403:
            # Both "insufficient permission" (scope missing) and generic 403
            # land here; the canonical UI message is the same — re-auth.
            if "insufficient permission" in lower or "insufficientpermissions" in lower:
                raise HTTPException(
                    status_code=403, detail="gmail_modify_scope_missing"
                ) from exc
            raise HTTPException(
                status_code=403, detail=f"gmail_forbidden: {raw[:200]}"
            ) from exc
        logger.warning(
            "emails.trash.google_error",
            status_code=resp_status,
            error_reason=raw[:200],
        )
        raise HTTPException(
            status_code=502, detail=f"gmail_upstream: {raw[:200]}"
        ) from exc

    logger.info("emails.trash.success")
    return result


# ---------------------------------------------------------------------------
# POST /emails/headlines — Sprint V1 polish · F2 · one-sentence executive brief
# ---------------------------------------------------------------------------


class HeadlinesRequest(BaseModel):
    """Batch headline request — up to 10 emails per call."""

    email_ids: list[str] = Field(..., min_length=1, max_length=10)


class HeadlineItem(BaseModel):
    """One email + its LLM-generated executive headline."""

    id: str
    from_name: str | None
    from_email: str
    subject: str
    headline: str


class HeadlinesResponse(BaseModel):
    headlines: list[HeadlineItem]
    model_ms: int


@router.post("/emails/headlines", response_model=HeadlinesResponse)
def post_email_headlines(
    req: HeadlinesRequest,
    user: dict[str, Any] = _CurrentUser,
) -> Any:
    """One-sentence PT-PT executive headline per email (batch LLM call).

    Flow:
        1. Fetch each email via `gmail.get_message` (reuses the existing
           body-extraction + HTML-strip path). Sequential loop — `get_message`
           is sync; for N ≤ 10 the wall time is dominated by Gmail API and the
           Groq call, not by serial fetches.
        2. Collect email metadata into a list of dicts (id, from_name,
           from_email, subject, body_text) and pass to
           `email_headlines.generate_headlines` (ONE Groq round-trip).
        3. Zip headlines back with metadata; return.

    Behaviour on errors:
        - `RefreshError` mid-fetch → 401 + cleanup (same as other endpoints).
        - Individual Gmail fetch failure → skip that email (don't fail the
          whole batch; user sees the other headlines).
        - LLM failure / JSON drift → service returns subjects as fallback —
          endpoint still 200.

    Invariantes (CLAUDE.md §3 + LOGGING-POLICY):
        - Zero logs de `subject` / `body` / `headline`. Apenas `count` + `model_ms`.
    """
    fetched: list[dict[str, Any]] = []
    try:
        for email_id in req.email_ids:
            try:
                msg = gmail.get_message(user["sub"], email_id)
            except RefreshError:
                raise
            except Exception as exc:  # noqa: BLE001 — skip individual failures
                logger.warning(
                    "emails.headlines.fetch_skipped",
                    error_type=type(exc).__name__,
                )
                continue
            fetched.append(
                {
                    "id": msg.get("id", email_id),
                    "from_name": msg.get("from_name"),
                    "from_email": msg.get("from_email", ""),
                    "subject": msg.get("subject", ""),
                    "body_text": msg.get("body_text", ""),
                }
            )
    except RefreshError:
        return _invalid_grant_response(user["sub"])

    headlines, model_ms = email_headlines.generate_headlines(fetched)

    # Build response items by joining headline-by-id with metadata.
    by_id_meta = {m["id"]: m for m in fetched}
    items: list[HeadlineItem] = []
    for h in headlines:
        meta = by_id_meta.get(h["id"])
        if meta is None:
            continue
        items.append(
            HeadlineItem(
                id=h["id"],
                from_name=meta.get("from_name"),
                from_email=meta.get("from_email", ""),
                subject=meta.get("subject", ""),
                headline=h["headline"],
            )
        )

    logger.info(
        "emails.headlines.success",
        count=len(items),
        model_ms=model_ms,
    )
    return HeadlinesResponse(headlines=items, model_ms=model_ms)


# _invalid_grant_response imported from app.services.auth_helpers
