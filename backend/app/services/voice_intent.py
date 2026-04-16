"""Groq Llama 3.3 70B — intent classification for Vox agent.

Classifies user voice transcript into an intent + parameters so the
frontend can route the flow (read emails, reply, send, list, etc.).
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

_INTENT_SYSTEM_PROMPT_TEMPLATE = """És o Vox, agente vocal do Per4Biz. \
Classifica a intenção do utilizador num JSON deste formato:

{{"intent": "...", "params": {{...}}}}

CONTEXTO TEMPORAL ATUAL: {now_iso} ({now_human})
Timezone do utilizador: Europe/Lisbon

Intenções possíveis:
- "read_emails" — quer ler/ouvir emails. Params: {{"count": N, "filter": "unread"|"all"}}
- "reply" — quer responder a um email. Params: {{"to": "..."}} (se mencionado)
- "send" — quer enviar um draft. Params: {{}}
- "summarize" — quer um resumo dos emails. Params: {{"count": N}}
- "search" — quer procurar emails. Params: {{"query": "..."}}
- "calendar_list" — quer ver agenda. Params: {{"days": N}} (padrão: 7)
- "calendar_create" — quer criar evento. Params: \
{{"summary": "...", "start": "ISO_8601_COM_TZ", "end": "ISO_8601_COM_TZ", "location": "..."}}
- "calendar_edit" — quer alterar evento existente. Params: \
{{"summary": "...", "start": "ISO_8601_COM_TZ", "end": "ISO_8601_COM_TZ", "location": "..."}} — \
APENAS os campos a MUDAR. NUNCA incluir event_id (o frontend resolve o evento pelo contexto).
- "calendar_delete" — quer apagar evento. Params: {{}} — NUNCA event_id (frontend resolve contexto).
- "contacts_search" — procurar contacto. Params: {{"query": "..."}}
- "general" — conversa, pergunta, esclarecimento. Params: {{"text": "..."}}

REGRAS DE OURO:
1. Responde APENAS o JSON, sem markdown, sem explicação.
2. USA O HISTÓRICO da conversa para resolver referências como "amanhã", \
"essa reunião", "ele", "às 15h" → liga ao contexto anterior.
3. Para `calendar_create`, datas DEVEM ser ISO 8601 COMPLETO com offset \
timezone (+00:00 para Lisboa em inverno, +01:00 verão). \
Exemplo: "amanhã às 15h" → "{tomorrow_iso_15h}".
4. Se faltar duração, assume 1 hora (end = start + 1h).
5. Se ambíguo, escolhe a mais provável; nunca cries `general` para evitar \
trabalho — só `general` para conversa pura.
6. Para perguntas vagas como "como estás?", "obrigado", "olá" → general.
7. Para "marca reunião amanhã" SEM hora → calendar_create com \
start = amanhã 09:00 (assumir manhã útil).
8. Para `calendar_edit` e `calendar_delete`, o ID do evento NUNCA é necessário \
— o frontend mantém contexto do último evento discutido. Para editar, \
devolve SÓ os campos a mudar.

EXEMPLOS:
"lê os meus emails" → {{"intent": "read_emails", "params": {{"count": 3}}}}
"o que tenho na agenda?" → {{"intent": "calendar_list", "params": {{"days": 7}}}}
"marca reunião com a Maria amanhã às 15h" → \
{{"intent": "calendar_create", "params": {{"summary": "Reunião com Maria", \
"start": "{tomorrow_iso_15h}", "end": "{tomorrow_iso_16h}"}}}}
"cancela o evento" + histórico mostra reunião → \
{{"intent": "calendar_delete", "params": {{}}}}
"cancela essa reunião" + histórico mostra evento → \
{{"intent": "calendar_delete", "params": {{}}}}
"passa a reunião para sexta às 16h" + histórico mostra evento → \
{{"intent": "calendar_edit", "params": {{"start": "ISO_SEXTA_16H", "end": "ISO_SEXTA_17H"}}}}
"muda o local para o Starbucks" + histórico mostra evento → \
{{"intent": "calendar_edit", "params": {{"location": "Starbucks"}}}}
"qual o email do João Silva?" → \
{{"intent": "contacts_search", "params": {{"query": "João Silva"}}}}
"obrigado Vox" → {{"intent": "general", "params": {{"text": "obrigado Vox"}}}}
"""


def _build_intent_prompt() -> str:
    """Render the intent prompt with current temporal context (Europe/Lisbon)."""
    from datetime import datetime, timedelta, timezone

    # Lisbon = UTC+0 in winter, UTC+1 in summer. Use UTC offset detection from
    # zoneinfo if available, else fall back to UTC.
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Europe/Lisbon")
    except Exception:
        tz = timezone.utc

    now = datetime.now(tz)
    tomorrow = now + timedelta(days=1)
    tomorrow_15h = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
    tomorrow_16h = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0)

    return _INTENT_SYSTEM_PROMPT_TEMPLATE.format(
        now_iso=now.isoformat(timespec="seconds"),
        now_human=now.strftime("%A, %d %B %Y, %H:%M"),
        tomorrow_iso_15h=tomorrow_15h.isoformat(timespec="seconds"),
        tomorrow_iso_16h=tomorrow_16h.isoformat(timespec="seconds"),
    )


def classify_intent(
    transcript: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Classify user intent from voice transcript.

    Args:
        transcript: what the user said.
        history: prior conversation messages [{role, content}] for context.

    Returns:
        dict with keys: intent (str), params (dict), model_ms (int)
    """
    settings = get_settings()
    client = Groq(api_key=settings.GROQ_API_KEY, timeout=_HTTP_TIMEOUT)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _build_intent_prompt()},
    ]

    # Include last 6 turns for multi-turn reference resolution
    if history:
        for msg in history[-12:]:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"][:300]})

    messages.append({"role": "user", "content": transcript})

    t0 = time.monotonic()
    response = retry_with_backoff(
        client.chat.completions.create,
        model=settings.GROQ_LLM_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=300,
    )
    model_ms = int((time.monotonic() - t0) * 1000)

    raw: str = response.choices[0].message.content or ""

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(cleaned)
        intent = parsed.get("intent", "general")
        params = parsed.get("params", {})
    except (json.JSONDecodeError, KeyError):
        intent = "general"
        params = {"text": transcript}

    logger.info(
        "voice_llm.classify.ok",
        intent=intent,
        model_ms=model_ms,
        transcript_len=len(transcript),
    )

    return {"intent": intent, "params": params, "model_ms": model_ms}
