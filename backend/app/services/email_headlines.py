"""Groq Llama 3.3 70B — executive email headlines (one-sentence summaries).

Transforms a list of raw emails (sender + subject + body) into short,
factual PT-PT sentences — one per email — so the Vox agent can brief the
user like a senior secretary instead of reading bodies verbatim.

Contract:
    generate_headlines(emails) -> (headlines_list, model_ms)
    where `headlines_list` is [{"id": str, "headline": str}, ...] aligned by
    email id (not by index — the LLM may reorder; we look up by id).

Guardrails (CLAUDE.md §3 + LOGGING-POLICY):
    - ONE Groq round-trip for N emails (batch prompt) — not N individual calls.
    - temperature=0.2 (near-deterministic, slight room for better phrasing).
    - max_tokens scales with N (80 per email is generous for ≤12 words PT-PT).
    - Timeout 30s (same as voice_llm pattern).
    - Body truncated to 800 chars per email in the prompt (keeps token bill
      predictable and avoids drowning the model in signatures/disclaimers).
    - On JSON parse failure: fallback to `subject` as headline per email —
      never crash the user interaction.
    - ZERO logs of body / subject / headline content (all PII).
      Only `count` + `model_ms`.
"""

from __future__ import annotations

import json
import time
from typing import Any

from groq import Groq

from app.config import get_settings
from app.logging import get_logger
from app.services.retry import retry_with_backoff

logger = get_logger(__name__)

_HTTP_TIMEOUT = 30.0
_MAX_BODY_CHARS = 800
_TOKENS_PER_EMAIL = 80
_TEMPERATURE = 0.2

_HEADLINES_SYSTEM_PROMPT = """És o Vox, secretário sénior PT-PT. Dou-te uma lista de emails numerados com remetente, assunto e as primeiras linhas. Para cada email, produz UMA frase curta (máx 12 palavras) em PT-PT que captura a essência — NÃO leias verbatim.

Regras:
- Primeira pessoa do remetente em relação ao utilizador: "João quer marcar reunião", não "João escreveu sobre...".
- Verbo forte no presente: "João pede", "Maria confirma", "Pedro envia".
- Factos, não adjectivos: "Ana cancela a reunião de quinta" não "Ana enviou email importante sobre algo".
- Ignora assinaturas, disclaimers, promocional.
- Sem pontuação final.

Devolve APENAS um array JSON nesta forma (sem markdown):
[{"id": "<email_id_1>", "headline": "..."}, {"id": "<email_id_2>", "headline": "..."}, ...]
"""


def _build_user_message(emails: list[dict[str, Any]]) -> str:
    """Build the numbered email list the LLM sees.

    Format (one block per email):

        Email N (id: <email_id>)
        De: <from_name ou from_email>
        Assunto: <subject>
        Corpo: <body_text truncado a 800 chars>

        ---

    The `id` is injected so the model can round-trip it in the JSON
    response — we then look up metadata from the original list.
    """
    blocks: list[str] = []
    for idx, email in enumerate(emails, start=1):
        email_id = email.get("id", "")
        from_name = email.get("from_name") or email.get("from_email", "")
        subject = email.get("subject", "") or ""
        body_text = (email.get("body_text", "") or "")[:_MAX_BODY_CHARS]

        block = (
            f"Email {idx} (id: {email_id})\n"
            f"De: {from_name}\n"
            f"Assunto: {subject}\n"
            f"Corpo: {body_text}"
        )
        blocks.append(block)

    return "\n\n---\n\n".join(blocks)


def _parse_headlines(raw: str) -> list[dict[str, str]]:
    """Parse the LLM output into a list of {id, headline} dicts.

    Tolerates:
        - Markdown code fences (```json ... ```)
        - Leading/trailing whitespace
        - Extra prose before/after the array (rare with temp=0.2 + explicit
          instruction, but defensive)

    Raises `json.JSONDecodeError` / `ValueError` on unrecoverable parse errors —
    caller (`generate_headlines`) catches and falls back to subjects.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Strip ```json\n...\n``` fence
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    # If the model prepended prose, try to extract the first `[...]` span.
    if not cleaned.startswith("["):
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("no JSON array found in LLM response")
        cleaned = cleaned[start : end + 1]

    parsed = json.loads(cleaned)
    if not isinstance(parsed, list):
        raise ValueError("LLM response is not a JSON array")

    out: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        headline = item.get("headline")
        item_id = item.get("id")
        if not isinstance(headline, str) or not isinstance(item_id, str):
            continue
        out.append({"id": item_id, "headline": headline.strip().rstrip(".。!?")})
    return out


def generate_headlines(
    emails: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], int]:
    """Generate one-sentence PT-PT headlines for a batch of emails.

    Args:
        emails: list of dicts (max 10 in practice, enforced by the router).
            Each dict must have: `id`, `from_email`. Optional: `from_name`,
            `subject`, `body_text`. Any missing keys default to empty string
            — the LLM handles sparse context gracefully.

    Returns:
        Tuple `(headlines_list, model_ms)` where:
            - `headlines_list` is `[{"id": str, "headline": str}, ...]` with
              one entry per input email (fallback fills missing ids with the
              email's subject).
            - `model_ms` is the LLM latency in milliseconds.

    On LLM failure (exception after retries) or JSON parse failure the
    function returns a fallback list using each email's subject as headline,
    so the caller never crashes on this interaction. `model_ms` still
    reflects the attempted call (or 0 if the exception happened before the
    clock was captured).
    """
    if not emails:
        return ([], 0)

    settings = get_settings()
    n = len(emails)
    max_tokens = _TOKENS_PER_EMAIL * n

    user_content = _build_user_message(emails)

    t0 = time.monotonic()
    model_ms = 0
    raw: str = ""

    try:
        client = Groq(api_key=settings.GROQ_API_KEY, timeout=_HTTP_TIMEOUT)
        response = retry_with_backoff(
            client.chat.completions.create,
            model=settings.GROQ_LLM_MODEL,
            messages=[
                {"role": "system", "content": _HEADLINES_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=_TEMPERATURE,
            max_tokens=max_tokens,
        )
        model_ms = int((time.monotonic() - t0) * 1000)
        raw = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 — must not crash the caller
        model_ms = int((time.monotonic() - t0) * 1000)
        logger.warning(
            "emails.headlines.llm_failed",
            count=n,
            model_ms=model_ms,
            error_type=type(exc).__name__,
        )
        return (_fallback_headlines(emails), model_ms)

    try:
        parsed = _parse_headlines(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(
            "emails.headlines.parse_failed",
            count=n,
            model_ms=model_ms,
            error_type=type(exc).__name__,
        )
        return (_fallback_headlines(emails), model_ms)

    # Build an id → headline lookup and pair back with original emails so we
    # always emit exactly `n` entries in the same order as input. Missing ids
    # in the LLM response fall back to subject.
    by_id: dict[str, str] = {item["id"]: item["headline"] for item in parsed}
    result: list[dict[str, str]] = []
    missing = 0
    for email in emails:
        email_id = email.get("id", "")
        headline = by_id.get(email_id)
        if not headline:
            missing += 1
            headline = (email.get("subject") or "").strip() or "(sem assunto)"
        result.append({"id": email_id, "headline": headline})

    logger.info(
        "emails.headlines.ok",
        count=n,
        model_ms=model_ms,
        missing_from_llm=missing,
    )
    return (result, model_ms)


def _fallback_headlines(emails: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build headlines from subjects when the LLM path fails.

    This keeps Vox alive even under Groq outages / JSON drift — the user
    still sees a brief (just less polished) briefing instead of a crash.
    """
    out: list[dict[str, str]] = []
    for email in emails:
        subject = (email.get("subject") or "").strip() or "(sem assunto)"
        out.append({"id": email.get("id", ""), "headline": subject})
    return out
