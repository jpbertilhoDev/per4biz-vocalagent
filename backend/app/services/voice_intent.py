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

_INTENT_SYSTEM_PROMPT = """És o Vox, o agente vocal do Per4Biz. O utilizador falou para ti. \
Classifica a intenção dele num JSON com este formato:

{"intent": "...", "params": {...}}

Intenções possíveis:
- "read_emails" — quer ler/ouvir emails. Params: {"count": N, "filter": "unread"|"all"}
- "reply" — quer responder a um email. Params: {"to": "..."} (se mencionado)
- "send" — quer enviar um draft. Params: {}
- "summarize" — quer um resumo dos emails. Params: {"count": N}
- "search" — quer procurar emails. Params: {"query": "..."}
- "calendar_list" — quer ver a agenda / compromissos. Params: {"days": N} (padrão: 7)
- "calendar_create" — quer criar um evento. Params: {"summary": "...", "start": "...", "end": "..."} (datas em ISO 8601 se possível)
- "calendar_edit" — quer editar um evento. Params: {"event_id": "..."} (se conhecido)
- "calendar_delete" — quer apagar um evento. Params: {"event_id": "..."} (se conhecido)
- "contacts_search" — quer procurar um contacto. Params: {"query": "..."}
- "general" — conversa geral / pergunta. Params: {"text": "..."}

Regras:
- Responde APENAS com o JSON, sem markdown, sem explicação.
- Se ambíguo, escolhe a intenção mais provável.
- "lê os meus emails" / "quero ouvir os emails" / "mostra inbox" = read_emails
- "responde ao João" / "quero responder" = reply
- "envia" / "manda" = send
- "resumo" / "sumariza" = summarize
- "agenda" / "compromissos" / "reuniões" / "o que tenho hoje" / "amanhã" = calendar_list
- "cria evento" / "marca reunião" / "marcar compromisso" = calendar_create
- "muda o evento" / "editar reunião" = calendar_edit
- "apaga o evento" / "cancelar reunião" = calendar_delete
- "procura contacto" / "qual o email do João" / "telefone da Maria" = contacts_search
- Qualquer outra coisa = general
"""


def classify_intent(transcript: str) -> dict[str, Any]:
    """Classify user intent from voice transcript.

    Returns:
        dict with keys: intent (str), params (dict), model_ms (int)
    """
    settings = get_settings()
    client = Groq(api_key=settings.GROQ_API_KEY, timeout=_HTTP_TIMEOUT)

    t0 = time.monotonic()
    response = retry_with_backoff(
        client.chat.completions.create,
        model=settings.GROQ_LLM_MODEL,
        messages=[
            {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        temperature=0.1,
        max_tokens=200,
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
