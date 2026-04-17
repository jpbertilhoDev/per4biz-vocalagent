"""
Wrapper server-side do Gmail v1 API (Sprint 1.x · E2 · SPEC §6 / RF-2.1 + RF-2.6).

Exposto:
    - `list_messages(user_id, page_token=None, limit=50) -> dict` — lista inbox
      com metadados prontos para UI (AC-2.1 · RF-2.6).
    - `get_message(user_id, message_id) -> dict` — abre email com `body_text`
      sanitizado (HTML strippado via `html.parser.HTMLParser`).
    - `_get_valid_credentials(user_id)` — lê `google_accounts`, decifra tokens,
      faz refresh silencioso se `expired`, persiste novo `access_token`
      cifrado (AC-2.6). Propaga `RefreshError` bruta (AC-2.7 — router trata
      cleanup + 401).
    - `_html_to_text(html)` — tira tags, ignora `<script>`/`<style>`,
      normaliza whitespace.

Invariantes de segurança (CLAUDE.md §3, LOGGING-POLICY.md):
    - Zero logs de PII: bodies, subjects, from_email, tokens cifrados ou
      decifrados. Apenas contagens (`email_count`), flags (`refreshed=True`)
      e identificadores anonimizados (`gmail_message_id` é tratado como ID
      opaco — não é PII).
    - Tokens em memória apenas o estritamente necessário; nunca retornados
      fora deste módulo.
    - Refresh tokens são cifrados em repouso (AES-256-GCM via `app.services.crypto`).

Formato de `refresh_token_encrypted` / `access_token_encrypted`:
    O Supabase pode entregar bytea como `bytes` cru (cliente Python `supabase`
    com colunas nativas) ou como string `"\\x<hex>"` (formato PostgREST quando
    gravamos via upsert de string — ver `app.routers.auth` linha ~144).
    `_decode_bytea` lida com ambos. Escrita é sempre no formato `"\\x<hex>"`
    para consistência com o auth.py.
"""

from __future__ import annotations

import base64
import re
from datetime import UTC, datetime, timedelta
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any, cast

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient import discovery

from app.config import get_settings
from app.logging import get_logger
from app.services import crypto, supabase_client

logger = get_logger(__name__)

_TOKEN_URI = "https://oauth2.googleapis.com/token"  # noqa: S105 — URL pública, não secret
_BODY_MAX_CHARS = 100_000  # limite V1 — evita explosão em emails HTML grandes
_DEFAULT_LIST_LIMIT = 50


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _decode_bytea(value: bytes | str) -> bytes:
    """Converte uma coluna bytea devolvida pelo Supabase em `bytes` raw.

    Aceita:
        - `bytes` já cru (cliente `supabase-py` em certas versões).
        - `str` no formato `"\\x<hex>"` (PostgREST / payloads upserted em
          `app.routers.auth`).

    Raises:
        ValueError: se o formato for desconhecido.
    """
    if isinstance(value, bytes):
        return value
    if isinstance(value, str) and value.startswith("\\x"):
        return bytes.fromhex(value[2:])
    raise ValueError(f"unexpected bytea format: {type(value).__name__}")


def _encode_bytea(value: bytes) -> str:
    """Serializa `bytes` como `"\\x<hex>"` — formato que o PostgREST aceita
    para colunas bytea via JSON body (idêntico ao usado em `auth.callback`).
    """
    return f"\\x{value.hex()}"


def _select_primary_account(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Escolhe a conta primária entre as rows devolvidas pelo Supabase.

    Preferência: `is_primary=True`. Fallback: primeira row. Raises se vazio.
    """
    if not rows:
        raise LookupError("no google_accounts row found for user")
    for row in rows:
        if row.get("is_primary"):
            return row
    return rows[0]


# ---------------------------------------------------------------------------
# Credenciais (com refresh silencioso)
# ---------------------------------------------------------------------------


def _get_valid_credentials(user_id: str) -> Credentials:
    """Constrói `Credentials` válidas para o `user_id`, fazendo refresh se preciso.

    Flow (AC-2.6 · SPEC §6 · RF-2.1):
        1. Carrega row de `google_accounts` via Supabase admin client.
        2. Decifra `refresh_token_encrypted` (+ `access_token_encrypted` se existir).
        3. Constrói `google.oauth2.credentials.Credentials`.
        4. Se `credentials.expired` → `credentials.refresh(Request())`.
        5. Se houve refresh: cifra novo `access_token`, persiste em
           `google_accounts.access_token_encrypted` + novo
           `access_token_expires_at = now + 1h` (Google devolve tipicamente
           `expires_in=3600`; usamos o novo `credentials.expiry` se presente).

    Propaga `google.auth.exceptions.RefreshError` sem engolir — o router
    `/emails/*` captura e faz cleanup (AC-2.7).
    """
    settings = get_settings()
    sb = supabase_client.get_supabase_admin()

    rows = cast(
        "list[dict[str, Any]]",
        sb.table("google_accounts").select("*").eq("user_id", user_id).execute().data,
    )
    row = _select_primary_account(rows)

    refresh_token = _decode_bytea(row["refresh_token_encrypted"])
    refresh_plaintext = crypto.decrypt(refresh_token).decode("utf-8")

    access_plaintext: str | None = None
    access_cipher = row.get("access_token_encrypted")
    if access_cipher:
        access_bytes = _decode_bytea(access_cipher)
        access_plaintext = crypto.decrypt(access_bytes).decode("utf-8")

    # `google.oauth2.credentials.Credentials.__init__` não tem anotações
    # completas nos stubs; chamada segura com kwargs verificados. O patch
    # em testes (`app.services.gmail.Credentials`) substitui este binding.
    credentials = Credentials(  # type: ignore[no-untyped-call]
        token=access_plaintext,
        refresh_token=refresh_plaintext,
        token_uri=_TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=row.get("scopes") or [],
    )

    if credentials.expired:
        # Propaga RefreshError raw — router trata cleanup + 401.
        credentials.refresh(Request())
        logger.info("gmail.credentials.refreshed", account_id=row.get("id"))

        new_token = credentials.token
        if new_token:
            new_expiry = getattr(credentials, "expiry", None)
            if new_expiry is None:
                new_expiry_iso = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
            else:
                # `credentials.expiry` é naive-UTC na lib google-auth.
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


# ---------------------------------------------------------------------------
# HTML → texto (stdlib)
# ---------------------------------------------------------------------------


class _HTMLStripper(HTMLParser):
    """Parser stdlib que remove tags e ignora `<script>` / `<style>`.

    Tags de bloco (`<br>`, `<p>`, `<div>`, `<li>`, `<h1..h6>`) inserem newline
    para preservar a estrutura mínima (TTS precisa de pausas naturais).
    """

    _BLOCK_TAGS = frozenset({"br", "p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"})
    _SKIP_TAGS = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # `attrs` é parte da interface de HTMLParser; não usamos em V1.
        del attrs
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Self-closing (<br/>) — insere newline mesmo sem endtag.
        del attrs
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Normaliza runs de espaços/tabs, preserva newlines significativos,
        # colapsa newlines triplos em duplo.
        collapsed = re.sub(r"[ \t]+", " ", raw)
        collapsed = re.sub(r"\n\s*\n\s*\n+", "\n\n", collapsed)
        return collapsed.strip()


def _html_to_text(html: str) -> str:
    """Converte HTML em texto plano via stdlib `HTMLParser` (RF-2.1 · SPEC §4).

    - Remove todas as tags.
    - Ignora conteúdo dentro de `<script>` / `<style>`.
    - Preserva texto visível; normaliza whitespace.
    """
    stripper = _HTMLStripper()
    stripper.feed(html)
    stripper.close()
    return stripper.get_text()


# ---------------------------------------------------------------------------
# Helpers de parsing Gmail
# ---------------------------------------------------------------------------


def _headers_map(msg: dict[str, Any]) -> dict[str, str]:
    """Constrói um dict case-insensitive de headers a partir de `payload.headers`.

    Gmail devolve uma lista `[{"name": "...", "value": "..."}]`. Normalizamos
    para minúsculas para lookup robusto (`From` / `FROM` / `from` → `from`).
    """
    headers_list = msg.get("payload", {}).get("headers", []) or []
    return {h.get("name", "").lower(): h.get("value", "") for h in headers_list}


def _parse_address_list(raw: str) -> list[str]:
    """Extrai lista de emails de um header tipo `To:` / `Cc:`.

    Usa `email.utils.getaddresses` via `parseaddr` em cada fragmento separado
    por vírgula — suficiente para V1; sem edge cases RFC 2822 complexos.
    """
    if not raw:
        return []
    # Simplistic split — suficiente para V1 (sem nested groups RFC 2822).
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    emails: list[str] = []
    for part in parts:
        _name, addr = parseaddr(part)
        if addr:
            emails.append(addr)
    return emails


def _parse_received_at(headers: dict[str, str], internal_date: str | None) -> str:
    """Retorna `received_at` ISO 8601 UTC.

    Prioridade:
        1. Header `Date:` parsed via RFC 2822 (`parsedate_to_datetime`).
        2. `message.internalDate` (ms epoch) — sempre presente na Gmail API.
        3. Fallback: `datetime.now(UTC)` (nunca deve ocorrer na prática).
    """
    date_header = headers.get("date")
    if date_header:
        try:
            dt = parsedate_to_datetime(date_header)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.isoformat()
        except (TypeError, ValueError):
            pass
    if internal_date:
        try:
            ms = int(internal_date)
            return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()
        except (TypeError, ValueError):
            pass
    return datetime.now(UTC).isoformat()


def _parse_metadata(msg: dict[str, Any]) -> dict[str, Any]:
    """Extrai metadados de um message Gmail (RF-2.6).

    Campos devolvidos: `id`, `from_name`, `from_email`, `subject`, `snippet`,
    `received_at` (ISO 8601 UTC), `is_unread`.
    """
    headers = _headers_map(msg)

    from_header = headers.get("from", "")
    name, addr = parseaddr(from_header) if from_header else ("", "")
    from_name = name or None
    from_email = addr or ""

    subject = headers.get("subject", "") or ""
    snippet = msg.get("snippet", "") or ""
    label_ids = msg.get("labelIds", []) or []
    is_unread = "UNREAD" in label_ids

    received_at = _parse_received_at(headers, msg.get("internalDate"))

    return {
        "id": msg.get("id", ""),
        "from_name": from_name,
        "from_email": from_email,
        "subject": subject,
        "snippet": snippet,
        "received_at": received_at,
        "is_unread": is_unread,
    }


def _b64url_decode(data: str) -> bytes:
    """Base64 URL-safe decode com padding automático.

    A Gmail API entrega bodies em base64url sem padding `=`. Adicionamos o
    número exacto de `=` em falta para que `urlsafe_b64decode` não falhe.
    """
    if not data:
        return b""
    padding = (-len(data)) % 4
    return base64.urlsafe_b64decode(data + ("=" * padding))


def _iter_parts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Walk recursivo por todas as parts de um `payload` Gmail (incluindo raiz)."""
    out: list[dict[str, Any]] = [payload]
    for part in payload.get("parts", []) or []:
        out.extend(_iter_parts(part))
    return out


def _extract_body_text(msg: dict[str, Any]) -> str:
    """Extrai `body_text` legível de um message Gmail (`format=full`).

    Prioridade:
        1. Concatena todas as parts `text/plain` (decoded).
        2. Se não houver plain, concatena todas as parts `text/html` e passa
           por `_html_to_text`.
        3. Fallback: string vazia.

    Trunca em `_BODY_MAX_CHARS` (100k chars) para proteger o TTS/LLM
    downstream contra emails HTML enormes.
    """
    payload = msg.get("payload", {})
    parts = _iter_parts(payload)

    plain_chunks: list[str] = []
    html_chunks: list[str] = []

    for part in parts:
        mime = part.get("mimeType", "")
        body = part.get("body", {}) or {}
        data = body.get("data")
        if not data:
            continue
        try:
            decoded = _b64url_decode(data).decode("utf-8", errors="replace")
        except (ValueError, UnicodeDecodeError):
            continue
        if mime == "text/plain":
            plain_chunks.append(decoded)
        elif mime == "text/html":
            html_chunks.append(decoded)

    if plain_chunks:
        text = "\n".join(plain_chunks)
    elif html_chunks:
        text = _html_to_text("\n".join(html_chunks))
    else:
        text = ""

    if len(text) > _BODY_MAX_CHARS:
        text = text[:_BODY_MAX_CHARS]
    return text


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def list_messages(
    user_id: str,
    page_token: str | None = None,
    limit: int = _DEFAULT_LIST_LIMIT,
) -> dict[str, Any]:
    """Lista os últimos `limit` emails da inbox (AC-2.1 · RF-2.6).

    Args:
        user_id: UUID do user (V1 fixo em `settings.USER_ID`).
        page_token: cursor opaco da Gmail API (`nextPageToken` da chamada prévia).
        limit: máximo de mensagens (default 50 — SPEC §6).

    Returns:
        ``{"emails": [...], "next_page_token": str | None}`` onde cada email
        contém `id`, `from_name`, `from_email`, `subject`, `snippet`,
        `received_at`, `is_unread`.

    Raises:
        google.auth.exceptions.RefreshError: refresh_token revogado (AC-2.7).
    """
    creds = _get_valid_credentials(user_id)
    service = discovery.build("gmail", "v1", credentials=creds, cache_discovery=False)

    list_response: dict[str, Any] = (
        service.users()
        .messages()
        .list(userId="me", maxResults=limit, pageToken=page_token, q="in:inbox")
        .execute()
    )

    message_refs = list_response.get("messages", []) or []
    next_page_token = list_response.get("nextPageToken")

    emails: list[dict[str, Any]] = []
    for ref in message_refs:
        msg_id = ref.get("id")
        if not msg_id:
            continue
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg_id,
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        emails.append(_parse_metadata(msg))

    logger.info("gmail.list", email_count=len(emails), has_next_page=next_page_token is not None)
    return {"emails": emails, "next_page_token": next_page_token}


def get_message(user_id: str, message_id: str) -> dict[str, Any]:
    """Abre um email específico com `body_text` sanitizado (AC-2.2 · SPEC §6).

    Args:
        user_id: UUID do user (V1 fixo em `settings.USER_ID`).
        message_id: `id` devolvido por `list_messages`.

    Returns:
        Dict com `id`, `from_name`, `from_email`, `to_emails`, `cc_emails`,
        `subject`, `snippet`, `body_text`, `received_at`, `is_unread`.

    Raises:
        google.auth.exceptions.RefreshError: refresh_token revogado (AC-2.7).
    """
    creds = _get_valid_credentials(user_id)
    service = discovery.build("gmail", "v1", credentials=creds, cache_discovery=False)

    msg: dict[str, Any] = (
        service.users().messages().get(userId="me", id=message_id, format="full").execute()
    )

    meta = _parse_metadata(msg)
    headers = _headers_map(msg)
    body_text = _extract_body_text(msg)

    logger.info("gmail.get", body_length=len(body_text))

    return {
        **meta,
        "to_emails": _parse_address_list(headers.get("to", "")),
        "cc_emails": _parse_address_list(headers.get("cc", "")),
        "body_text": body_text,
    }


def send_message(
    user_id: str,
    to: str,
    subject: str,
    body: str,
    in_reply_to: str | None = None,
) -> dict[str, Any]:
    """Envia um email via Gmail API (SPEC §3 · RF-V.4 · AC-E2.US3-1).

    Flow:
        1. `_get_valid_credentials(user_id)` — decifra tokens + refresh silencioso.
        2. Lookup primary `google_accounts.google_email` para o header ``From:``.
        3. Build RFC 5322 via ``MIMEText`` (UTF-8) + ``email.header.Header``
           no ``Subject:`` para acentos PT-PT corretos.
        4. Se ``in_reply_to`` presente, adiciona headers ``In-Reply-To`` +
           ``References`` para threading correto no Gmail web/app.
        5. Encode ``base64url`` sem padding; chamada
           ``service.users().messages().send(userId="me", body={"raw": ...})``.

    Args:
        user_id: UUID do user (V1 fixo em `settings.USER_ID`).
        to: destinatário (já validado como ``EmailStr`` no router).
        subject: assunto (unicode — PT-PT acentos tratados via ``Header``).
        body: corpo texto plano (``text/plain; charset=utf-8``).
        in_reply_to: ``gmail_message_id`` original em caso de reply (opcional).

    Returns:
        ``{"message_id": str, "thread_id": str}`` com IDs devolvidos pelo Gmail.

    Raises:
        google.auth.exceptions.RefreshError: refresh_token revogado (AC-2.7).

    Invariantes (CLAUDE.md §3 + LOGGING-POLICY):
        - Zero logs de ``to`` / ``subject`` / ``body`` — apenas IDs opacos
          e flags booleanas (``has_reply``).
    """
    creds = _get_valid_credentials(user_id)

    # Lookup primary account email para FROM header. Best-effort — se por
    # qualquer razão a row não existir aqui (edge case após race condition),
    # o Gmail continua a aceitar o envio usando o mail da conta autenticada
    # (userId="me"), apenas o header From do MIME fica vazio.
    sb = supabase_client.get_supabase_admin()
    rows = cast(
        "list[dict[str, Any]]",
        sb.table("google_accounts")
        .select("google_email")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
        .data,
    )
    from_email = rows[0]["google_email"] if rows else ""

    # Build RFC 5322 — UTF-8 para suportar PT-PT acentos no body e subject.
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = str(Header(subject, "utf-8"))
    if from_email:
        msg["From"] = from_email
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8").rstrip("=")

    service = discovery.build("gmail", "v1", credentials=creds, cache_discovery=False)
    response: dict[str, Any] = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )

    logger.info(
        "gmail.send.ok",
        has_reply=in_reply_to is not None,
        gmail_message_id=response.get("id", ""),
    )
    return {
        "message_id": response.get("id", ""),
        "thread_id": response.get("threadId", ""),
    }


def trash_message(user_id: str, message_id: str) -> dict[str, Any]:
    """Move a Gmail message to trash (Sprint V1 polish · F-Delete).

    Wraps ``users.messages.trash`` which is reversible — the message stays in
    Gmail's Trash folder for 30 days and the user can restore it from the web
    UI. We deliberately do NOT use ``users.messages.delete`` (permanent).

    Scope required: ``https://www.googleapis.com/auth/gmail.modify`` — already
    requested by ``app.routers.auth`` at OAuth start. If the scope is missing
    (user authorized before the scope was added) Google returns 403
    ``insufficient permission`` and the router translates it into
    ``gmail_modify_scope_missing`` so the UI can prompt re-auth.

    Args:
        user_id: UUID do user (V1 fixo em ``settings.USER_ID``).
        message_id: Gmail message id devolvido por ``list_messages`` /
            ``get_message``.

    Returns:
        ``{"id": <message_id>, "labelIds": [...]}`` — the labels will now
        include ``"TRASH"`` on success.

    Raises:
        google.auth.exceptions.RefreshError: refresh_token revogado (AC-2.7).
        googleapiclient.errors.HttpError: propagada bruta — router traduz
            404 → email_not_found, 403 → gmail_modify_scope_missing, etc.

    Invariantes (CLAUDE.md §3 + LOGGING-POLICY):
        - Zero logs de subject/body. Apenas ID parcial anonimizado para
          correlação em Axiom/Sentry.
    """
    creds = _get_valid_credentials(user_id)
    service = discovery.build("gmail", "v1", credentials=creds, cache_discovery=False)

    result: dict[str, Any] = (
        service.users().messages().trash(userId="me", id=message_id).execute()
    )

    logger.info("gmail.trash.ok", gmail_message_id=message_id[:8])
    return {
        "id": result.get("id", ""),
        "labelIds": result.get("labelIds", []) or [],
    }
