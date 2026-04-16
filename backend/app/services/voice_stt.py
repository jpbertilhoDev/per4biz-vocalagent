"""Groq Whisper v3 STT service (SPEC §3 RF-V.1 · Sprint 2 · E4 · Task 2).

Wrapper server-side síncrono do Groq Whisper. Recebe bytes de áudio
(audio/webm opus vindo do MediaRecorder browser), envia ao endpoint
`audio.transcriptions.create` em modo `verbose_json` e devolve
`{text, language, duration_ms}`.

Regras:
- Fail-fast: `len(audio_bytes) > 1 MiB` → `ValueError` antes de tocar na API.
- SDK síncrono (`Groq`): FastAPI TestClient síncrono — ver PLAN §Risks.
- Zero logs de `text` (transcript é PII — LOGGING-POLICY.md).
- `groq.APIError` propaga raw; router `/voice/transcribe` traduz em 502
  (ERROR-MATRIX §voice).
"""
from __future__ import annotations

from typing import Any

from groq import Groq

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)

MAX_AUDIO_BYTES = 1_048_576  # 1 MiB — SPEC §3 / RF-V.1


def transcribe(audio_bytes: bytes, mime: str = "audio/webm") -> dict[str, Any]:
    """Transcreve áudio PT-PT via Groq Whisper v3.

    Args:
        audio_bytes: conteúdo binário do ficheiro (opus/webm típico).
        mime: content-type upstream; default `audio/webm`.

    Returns:
        dict com chaves:
            - `text` (str): transcript
            - `language` (str | None): ISO-639 detectado ou None
            - `duration_ms` (int): duração em milissegundos (0 se SDK não fornecer)

    Raises:
        ValueError: quando `len(audio_bytes) > 1 MiB`.
        groq.APIError: propagado do SDK (router traduz em 502).
    """
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError(
            f"audio too large: {len(audio_bytes)} bytes > {MAX_AUDIO_BYTES}"
        )

    settings = get_settings()
    client = Groq(api_key=settings.GROQ_API_KEY)

    result = client.audio.transcriptions.create(
        file=("audio.webm", audio_bytes, mime),
        model=settings.GROQ_STT_MODEL,
        response_format="verbose_json",
        language="pt",
    )

    duration_seconds = getattr(result, "duration", None) or 0.0
    duration_ms = int(duration_seconds * 1000)

    # NOTA: nunca logar `result.text` — transcript é PII (LOGGING-POLICY).
    logger.info(
        "voice_stt.transcribe.ok",
        bytes_len=len(audio_bytes),
        duration_ms=duration_ms,
    )

    return {
        "text": result.text,
        "language": getattr(result, "language", None),
        "duration_ms": duration_ms,
    }
