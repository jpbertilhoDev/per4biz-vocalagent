"""Portuguese-aware date normalization for calendar operations.

Used by the /calendar router to translate natural-language inputs like
"próxima quinta às 15h" or "amanhã" into ISO 8601 datetimes with
Europe/Lisbon offset.

The intent classifier (voice_intent.py) already tries to produce ISO, but
this is a safety net for when the LLM outputs Portuguese strings.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

try:
    from zoneinfo import ZoneInfo

    LISBON_TZ: Any = ZoneInfo("Europe/Lisbon")
except Exception:
    LISBON_TZ = UTC


# Ordered mapping for PT → digit conversion of small cardinal/ordinal words.
_PT_NUMBER_WORDS: dict[str, str] = {
    "uma": "1",
    "duas": "2",
    "dois": "2",
    "três": "3",
    "tres": "3",
    "quatro": "4",
    "cinco": "5",
    "seis": "6",
    "sete": "7",
    "oito": "8",
    "nove": "9",
    "dez": "10",
}

# PT weekdays → EN. dateparser handles EN weekday names reliably, and when
# combined with PREFER_DATES_FROM=future it naturally returns "the next
# <weekday>", which matches the PT "próxima <weekday>" semantics.
_PT_WEEKDAYS: dict[str, str] = {
    "segunda": "monday",
    "terça": "tuesday",
    "terca": "tuesday",
    "quarta": "wednesday",
    "quinta": "thursday",
    "sexta": "friday",
    "sábado": "saturday",
    "sabado": "saturday",
    "domingo": "sunday",
}

# "daqui a N <unit>" → "in N <unit>s". dateparser's native "in N units"
# English parser is robust; the PT equivalent often fails.
_PT_UNITS: dict[str, str] = {
    "dia": "day",
    "semana": "week",
    "mês": "month",
    "mes": "month",
    "ano": "year",
    "hora": "hour",
    "minuto": "minute",
}


def _preprocess_pt(raw: str) -> str:
    """Normalize PT natural-language quirks that dateparser misses.

    Order matters — each rule assumes the previous ones already ran.
    Returns a lowercase string suitable to feed into dateparser.
    """
    s = raw.lower().strip()

    # 1) PT number words → digits ("duas semanas" → "2 semanas").
    for word, digit in _PT_NUMBER_WORDS.items():
        s = re.sub(r"\b" + word + r"\b", digit, s)

    # 2) "daqui a N <unit>" → "in N <unit>s" BEFORE we strip the preposition "a".
    for pt_unit, en_unit in _PT_UNITS.items():
        pattern = r"daqui\s+a\s+(\d+)\s+" + pt_unit + r"s?\b"
        s = re.sub(
            pattern,
            lambda m, en=en_unit: f"in {m.group(1)} {en}" + ("s" if int(m.group(1)) != 1 else ""),
            s,
        )

    # 3) "15h" / "15h30" → "15:00" / "15:30".
    s = re.sub(r"(\d{1,2})h(\d{2})", r"\1:\2", s)
    s = re.sub(r"(\d{1,2})h(?!\d|:)", r"\1:00", s)

    # 4) Strip the "-feira" suffix from weekdays ("quinta-feira" → "quinta").
    s = s.replace("-feira", "")

    # 5) Strip PT time preposition before digits ("às 15:00" → "15:00"). This
    #    must run AFTER step 2 so we don't destroy "daqui a 2 ...".
    s = re.sub(r"\b(às|ás|as)\s+(\d)", r"\2", s)

    # 6) Drop "próxima/próximo" — PREFER_DATES_FROM=future already biases
    #    bare weekdays to the next occurrence.
    s = re.sub(r"\bpróxim[ao]s?\b", "", s)
    s = re.sub(r"\bproxim[ao]s?\b", "", s)

    # 7) PT weekdays → EN weekdays.
    for pt_wd, en_wd in _PT_WEEKDAYS.items():
        s = re.sub(r"\b" + pt_wd + r"\b", en_wd, s)

    # Collapse whitespace introduced by strips.
    return re.sub(r"\s+", " ", s).strip()


def parse_pt_datetime(value: str | None) -> datetime | None:
    """Parse a Portuguese natural-language datetime into an aware datetime.

    Returns None when input is None, empty, or unparseable.
    """
    if not value or not isinstance(value, str):
        return None

    # Fast path — already ISO 8601
    try:
        # Accept both "2026-04-23T15:00:00+01:00" and "2026-04-23T15:00:00Z"
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LISBON_TZ)
        return parsed
    except (ValueError, TypeError):
        pass

    # Natural language — preprocess PT quirks then delegate to dateparser.
    import dateparser

    preprocessed = _preprocess_pt(value)
    if not preprocessed:
        return None

    result = dateparser.parse(
        preprocessed,
        languages=["pt", "en"],
        settings={
            "TIMEZONE": "Europe/Lisbon",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
            "DATE_ORDER": "DMY",
        },
    )
    if result is None:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=LISBON_TZ)
    return result


def ensure_iso_datetime(value: str | None, *, fallback_hours_from_now: int | None = None) -> str | None:
    """Return ISO 8601 string for a natural-language datetime, or None.

    If `fallback_hours_from_now` is set and parsing fails, returns an ISO
    datetime that many hours from now (useful for end times when only start
    was given).
    """
    parsed = parse_pt_datetime(value)
    if parsed is not None:
        return parsed.isoformat()
    if fallback_hours_from_now is not None:
        return (datetime.now(LISBON_TZ) + timedelta(hours=fallback_hours_from_now)).isoformat()
    return None
