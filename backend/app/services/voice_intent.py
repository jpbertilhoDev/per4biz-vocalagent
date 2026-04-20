"""Groq Llama 3.3 70B — intent classification for Vox agent.

Classifies user voice transcript into an intent + parameters so the
frontend can route the flow (read emails, reply, send, list, etc.).
"""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

from groq import Groq

from app.config import get_settings
from app.logging import get_logger
from app.services import telemetry
from app.services.retry import retry_with_backoff

logger = get_logger(__name__)

_HTTP_TIMEOUT = 30.0

_INTENT_SYSTEM_PROMPT_TEMPLATE = """És o Vox, secretário sénior PT-PT. Classificas o pedido num JSON:
{{"intent": "...", "params": {{...}}}}

Agora: {now_iso} (Europe/Lisbon)

INTENTS (11):

EMAIL
- read_emails — "lê", "mostra emails", "o que recebi" · params: {{"count": N}}
- reply — "responde a X", "replica", "diz-lhe que..." · params: {{"to": "..."}}
- send — "envia", "manda" (SÓ se houver draft no histórico) · params: {{}}
- summarize — "resume", "briefing" · params: {{"count": N}}
- search — "procura email de X" · params: {{"query": "..."}}
- email_delete — "apaga esse email", "arquiva", "vai para o lixo", "remove esse" \
(sobre um email) · params: {{}} (frontend resolve pelo lastEmailRef)

AGENDA
- calendar_list — "agenda", "o que tenho hoje/semana", "compromissos" · params: {{"days": N}}
- calendar_create — "marca", "agenda reunião com X", "bloqueia", "lembra-me", \
"relembra-me", "não deixes esquecer" · params: \
{{"summary": "...", "start": "ISO", "end": "ISO", "location": "...", "is_reminder": bool}}
- calendar_edit — "muda", "altera", "passa para", "adia" · params: SÓ campos a mudar, NUNCA event_id
- calendar_delete — "cancela", "apaga", "remove", "desmarca", "tira da agenda" \
(sobre um evento) · params: {{}} (NUNCA event_id)

CONTACTOS
- contacts_search — "qual email de X", "número de X" · params: {{"query": "..."}}

FALLBACK
- general — cumprimento, conversa, OU ambiguidade genuína · params: {{"text": "..."}}

REGRAS:
1. Frase com gatilho claro → EXECUTA o intent. Não peças clarificação.
2. Datas em ISO 8601 com offset Lisboa. "amanhã às 15h" → "{tomorrow_iso_15h}". \
Sem hora explícita, assume 09:00. Sem duração, 1h.
3. LEMBRETES ("lembra-me de X daqui a Y", "relembra-me X em Z") → calendar_create com \
`is_reminder: true`, duração 5 minutos, summary é o conteúdo do lembrete (não "Lembrete: X"). \
Expressões de tempo suportadas: "daqui a 2 horas", "em 30 minutos", "amanhã 10h", \
"hoje à tarde" (assume 15:00), "hoje à noite" (assume 20:00).
4. calendar_edit/delete: params APENAS campos a mudar. NUNCA event_id (frontend resolve).
5. Usa o histórico para resolver pronomes ("isso", "essa", "ele") e "amanhã às 15h".
6. Pronome SEM entidade no histórico ("apaga isso" vazio) → general + "ask_clarification": true.
7. "sim"/"ok"/"confirma" sozinho (confirmações por toque) → general + "ask_clarification": true.
8. Cumprimentos ("olá", "obrigado", "como estás?") → general SEM ask_clarification.
9. "Apaga" / "remove" / "cancela" ambíguo: usa o histórico para decidir entre \
email_delete e calendar_delete. Se o histórico recente tem um evento de agenda → \
calendar_delete. Se tem um email aberto ou listado → email_delete. Se tem os dois \
tipos recentes OU nenhum → general + "ask_clarification": true com text="É um \
evento ou um email?".

EXEMPLOS:
"lê os emails" → {{"intent":"read_emails","params":{{"count":3}}}}
"responde ao João" → {{"intent":"reply","params":{{}}}}
"envia" + draft no histórico → {{"intent":"send","params":{{}}}}
"o que tenho na agenda esta semana" → {{"intent":"calendar_list","params":{{"days":7}}}}
"marca reunião com Maria amanhã 15h" → {{"intent":"calendar_create","params":\
{{"summary":"Reunião com Maria","start":"{tomorrow_iso_15h}","end":"{tomorrow_iso_16h}"}}}}
"lembra-me daqui a 2 horas de ligar ao João" → {{"intent":"calendar_create","params":\
{{"summary":"Ligar ao João","start":"{reminder_in_2h_iso}","end":"{reminder_in_2h_end_iso}","is_reminder":true}}}}
"relembra-me amanhã 10h de preparar o relatório" → {{"intent":"calendar_create","params":\
{{"summary":"Preparar o relatório","start":"{tomorrow_iso_10h}","end":"{tomorrow_iso_10h05}","is_reminder":true}}}}
"cancela essa reunião" + histórico tem evento → {{"intent":"calendar_delete","params":{{}}}}
"passa para sexta 16h" + histórico tem evento → {{"intent":"calendar_edit","params":\
{{"start":"ISO_SEXTA_16H","end":"ISO_SEXTA_17H"}}}}
"muda o local para Starbucks" + histórico tem evento → {{"intent":"calendar_edit","params":\
{{"location":"Starbucks"}}}}
"apaga esse email" + histórico mostra email aberto → {{"intent":"email_delete","params":{{}}}}
"vai para o lixo" + histórico mostra email → {{"intent":"email_delete","params":{{}}}}
"arquiva" + histórico mostra email → {{"intent":"email_delete","params":{{}}}}
"desmarca a reunião" + histórico mostra evento → {{"intent":"calendar_delete","params":{{}}}}
"remove esse" + ambos recentes → {{"intent":"general","params":\
{{"text":"remove esse","ask_clarification":true}}}}
"qual o email da Maria Silva" → {{"intent":"contacts_search","params":{{"query":"Maria Silva"}}}}
"olá Vox" → {{"intent":"general","params":{{"text":"olá Vox"}}}}
"apaga isso" (sem histórico) → {{"intent":"general","params":\
{{"text":"apaga isso","ask_clarification":true}}}}
"sim" sozinho → {{"intent":"general","params":{{"text":"sim","ask_clarification":true}}}}

APENAS o JSON. Sem markdown, sem explicação. Se não cabe num intent → general.
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
    tomorrow_10h = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    tomorrow_10h05 = tomorrow.replace(hour=10, minute=5, second=0, microsecond=0)
    reminder_in_2h = now + timedelta(hours=2)
    reminder_in_2h_end = reminder_in_2h + timedelta(minutes=5)

    return _INTENT_SYSTEM_PROMPT_TEMPLATE.format(
        now_iso=now.isoformat(timespec="seconds"),
        now_human=now.strftime("%A, %d %B %Y, %H:%M"),
        tomorrow_iso_15h=tomorrow_15h.isoformat(timespec="seconds"),
        tomorrow_iso_16h=tomorrow_16h.isoformat(timespec="seconds"),
        tomorrow_iso_10h=tomorrow_10h.isoformat(timespec="seconds"),
        tomorrow_iso_10h05=tomorrow_10h05.isoformat(timespec="seconds"),
        reminder_in_2h_iso=reminder_in_2h.isoformat(timespec="seconds"),
        reminder_in_2h_end_iso=reminder_in_2h_end.isoformat(timespec="seconds"),
    )


def classify_intent(
    transcript: str,
    history: list[dict[str, str]] | None = None,
    *,
    session_id: UUID | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Classify user intent from voice transcript.

    Args:
        transcript: what the user said.
        history: prior conversation messages [{role, content}] for context.
        session_id: optional voice session UUID for phase telemetry.
        user_id: optional authenticated user UUID for phase telemetry.

    Returns:
        dict with keys: intent (str), params (dict), model_ms (int)
    """
    _emit = session_id is not None and user_id is not None
    t_phase = time.monotonic()
    if _emit:
        telemetry.emit_phase(session_id, user_id, "intent_start", 0, "ok")  # type: ignore[arg-type]

    try:
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
    except Exception:
        if _emit:
            telemetry.emit_phase(
                session_id,  # type: ignore[arg-type]
                user_id,  # type: ignore[arg-type]
                "intent_done",
                int((time.monotonic() - t_phase) * 1000),
                "error",
            )
        raise

    logger.info(
        "voice_llm.classify.ok",
        intent=intent,
        model_ms=model_ms,
        transcript_len=len(transcript),
    )

    if _emit:
        telemetry.emit_phase(
            session_id,  # type: ignore[arg-type]
            user_id,  # type: ignore[arg-type]
            "intent_done",
            int((time.monotonic() - t_phase) * 1000),
            "ok",
        )

    return {"intent": intent, "params": params, "model_ms": model_ms}
