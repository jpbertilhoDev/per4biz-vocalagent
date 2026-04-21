"""ElevenLabs TTS service (SPEC §3 RF-V.3 · Sprint 2 · E4 · Task 6).

Wrapper server-side síncrono do ElevenLabs Text-to-Speech. Recebe texto
PT-PT (resposta polida pelo Llama 3.3 70B no passo anterior do pipeline) e
devolve `{audio_bytes, mime, tts_ms}` — MP3 44.1 kHz / 128 kbps pronto para
reprodução via `<audio>` ou `MediaSource` no browser.

Regras:
- Fail-fast: `len(text) > 5000` → `ValueError` antes de instanciar o cliente
  (evita custo de créditos / latência desperdiçada em inputs absurdos).
- SDK síncrono (`ElevenLabs`): FastAPI TestClient síncrono — ver PLAN §Risks.
- Zero logs de `text` ou `audio_bytes` (ambos PII / conteúdo gerado — ver
  LOGGING-POLICY.md §4). Log apenas `tts_ms`, `text_len` e `bytes_len`.
- Qualquer exceção do SDK propaga raw; router `/voice/tts` (Task 6) traduz em
  502 com `error_code=voice.tts_upstream` (ERROR-MATRIX §voice).
"""

from __future__ import annotations

import time
from typing import Any

from elevenlabs.client import ElevenLabs

from app.config import get_settings
from app.logging import get_logger
from app.services.retry import retry_with_backoff

logger = get_logger(__name__)

MAX_TEXT_CHARS = 5000  # SPEC §3 / RF-V.3 — limite duro de input
_HTTP_TIMEOUT = 30.0


def synthesize(text: str, voice_id: str | None = None) -> dict[str, Any]:
    """Gera MP3 via ElevenLabs streaming e concatena chunks para bytes.

    Args:
        text: texto PT-PT a sintetizar (máx 5000 chars).
        voice_id: voice ID ElevenLabs. Se `None`, usa
            `settings.ELEVENLABS_VOICE_ID`.

    Returns:
        dict com chaves:
            - `audio_bytes` (bytes): MP3 44.1 kHz / 128 kbps concatenado.
            - `mime` (str): `"audio/mpeg"` (fixo — output_format `mp3_*`).
            - `tts_ms` (int): latência da chamada ao ElevenLabs em ms.

    Raises:
        ValueError: quando `len(text) > 5000` ou `voice_id` efectivo vazio.
        Exception: propagado do SDK (router traduz em 502).
    """
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"text too long: {len(text)} chars > {MAX_TEXT_CHARS}")

    settings = get_settings()
    effective_voice_id = voice_id or settings.ELEVENLABS_VOICE_ID
    if not effective_voice_id:
        raise ValueError("voice_id required but not provided or configured")

    client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY, timeout=_HTTP_TIMEOUT)

    t0 = time.monotonic()
    stream = retry_with_backoff(
        client.text_to_speech.convert,
        voice_id=effective_voice_id,
        model_id=settings.ELEVENLABS_MODEL_ID,
        text=text,
        output_format="mp3_44100_128",
    )
    audio_bytes = b"".join(stream)
    tts_ms = int((time.monotonic() - t0) * 1000)

    # NOTA: nunca logar `text` nem `audio_bytes` (PII — LOGGING-POLICY §4).
    # Apenas métricas numéricas.
    logger.info(
        "voice_tts.synthesize.ok",
        text_len=len(text),
        bytes_len=len(audio_bytes),
        tts_ms=tts_ms,
    )

    return {"audio_bytes": audio_bytes, "mime": "audio/mpeg", "tts_ms": tts_ms}
