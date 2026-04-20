"""Router `/voice` — pipeline vocal (Sprint 2 · E4 · SPEC §3 RF-V.1/V.2/V.3).

Endpoints (ordem do pipeline):
    - `POST /voice/transcribe` — upload de áudio (webm/opus) → transcript
      via Groq Whisper v3. RF-V.1.
    - `POST /voice/polish` — transcript + contexto do email recebido →
      resposta polida via Groq Llama 3.3 70B. RF-V.2.
    - `POST /voice/tts` — texto PT-PT → stream de áudio MP3 via ElevenLabs.
      RF-V.3. Response body é `StreamingResponse` `audio/mpeg`.

Invariantes (CLAUDE.md §3 + LOGGING-POLICY):
    - Todos os endpoints exigem `__Host-session` (via `current_user` dep);
      ausência / inválido → 401 (AC-6).
    - Zero logs de `audio_bytes`, `text`, `transcript` ou `polished_text`
      (tudo PII — LOGGING-POLICY §4). Apenas métricas numéricas + tipos de
      exceção.
    - Falhas upstream dos providers (Groq / ElevenLabs) traduzidas em 502
      com detail neutro (ERROR-MATRIX §voice).
    - Fail-fast (`ValueError` dos services) traduz em 413 para áudio
      oversize e 400 para texto oversize / voice_id em falta.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.deps import current_user
from app.logging import get_logger
from app.services import telemetry, voice_intent, voice_llm, voice_stt, voice_tts

logger = get_logger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

# Módulo-level singletons para parâmetros com call em default — evita B008
# (ruff). `Depends` e `File` são API do FastAPI: o valor passado via default
# é `FieldInfo/Depends`, não uma chamada "real". Extrair para constante do
# módulo satisfaz o linter sem alterar semântica (mesmo idiom em `emails.py`).
_CurrentUser = Depends(current_user)
_AudioFile = File(...)
_SessionIdHeader = Header(default=None, alias="X-Voice-Session-Id")

# Mirror do limite do serviço (`voice_tts.MAX_TEXT_CHARS`) para usar em
# `Field(max_length=...)` sem dependência circular de import-time.
_MAX_TTS_TEXT_CHARS = 5000


class PolishRequest(BaseModel):
    """Body de `POST /voice/polish` (RF-V.2).

    `transcript` é o output do STT. Os restantes campos são o contexto do
    email original (injectado pelo frontend) para o Llama gerar resposta
    coerente. Todos opcionais excepto `transcript`.
    """

    transcript: str = Field(..., min_length=1, max_length=2000)
    from_name: str = ""
    from_email: str = ""
    subject: str = ""
    body: str = ""


class TTSRequest(BaseModel):
    """Body de `POST /voice/tts` (RF-V.3)."""

    text: str = Field(..., min_length=1, max_length=_MAX_TTS_TEXT_CHARS)
    voice_id: str | None = None


class IntentRequest(BaseModel):
    """Body de `POST /voice/intent` — classifies user transcript into action."""

    transcript: str = Field(..., min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)


class ChatRequest(BaseModel):
    """Body de `POST /voice/chat` — conversational AI response."""

    transcript: str = Field(..., min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)


class TelemetryEvent(BaseModel):
    """One phase timing. Part of TelemetryBatch."""

    phase: str = Field(..., min_length=1, max_length=64)
    ms: int = Field(..., ge=0, le=120_000)
    status: str = Field("ok", pattern=r"^(ok|error|timeout)$")


class TelemetryBatch(BaseModel):
    """Batch of phase timings for one voice session."""

    events: list[TelemetryEvent] = Field(..., max_length=20)


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = _AudioFile,
    x_voice_session_id: UUID | None = _SessionIdHeader,
    user: dict[str, Any] = _CurrentUser,
) -> dict[str, Any]:
    """RF-V.1 — transcreve áudio PT-PT via Groq Whisper v3.

    Request: multipart/form-data com campo `audio` (webm/opus típico).
    Respostas:
        - 200 OK: `{text, language, duration_ms}`
        - 401: cookie ausente/inválido (via `current_user`).
        - 413: áudio > 1 MiB (fail-fast em `voice_stt.transcribe`).
        - 502: falha upstream Groq.
    """
    audio_bytes = await audio.read()
    try:
        result = voice_stt.transcribe(
            audio_bytes,
            mime=audio.content_type or "audio/webm",
            session_id=x_voice_session_id,
            user_id=str(user["sub"]),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001 — traduzir qualquer erro SDK em 502
        logger.warning(
            "voice.transcribe.upstream_fail",
            error_type=type(exc).__name__,
            user_sub=user["sub"],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="voice.stt_upstream",
        ) from exc

    # `result` já não contém PII em logs (apenas bytes_len / duration_ms);
    # o próprio serviço já fez `voice_stt.transcribe.ok`.
    logger.info("voice.transcribe.ok", user_sub=user["sub"])
    return result


@router.post("/polish")
def polish(
    req: PolishRequest,
    x_voice_session_id: UUID | None = _SessionIdHeader,
    user: dict[str, Any] = _CurrentUser,
) -> dict[str, Any]:
    """RF-V.2 — pole transcript em email PT-PT via Groq Llama 3.3 70B.

    Respostas:
        - 200 OK: `{polished_text, model_ms}`
        - 401: cookie ausente/inválido.
        - 422: validação Pydantic (transcript vazio / body > limites).
        - 502: falha upstream Groq.
    """
    context = {
        "from_name": req.from_name,
        "from_email": req.from_email,
        "subject": req.subject,
        "body": req.body,
    }
    try:
        result = voice_llm.polish_draft(
            req.transcript,
            context,
            session_id=x_voice_session_id,
            user_id=str(user["sub"]),
        )
    except Exception as exc:  # noqa: BLE001 — traduzir qualquer erro SDK em 502
        logger.warning(
            "voice.polish.upstream_fail",
            error_type=type(exc).__name__,
            user_sub=user["sub"],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="voice.llm_upstream",
        ) from exc
    logger.info("voice.polish.ok", user_sub=user["sub"])
    return result


@router.post("/tts")
def tts(
    req: TTSRequest,
    x_voice_session_id: UUID | None = _SessionIdHeader,
    user: dict[str, Any] = _CurrentUser,
) -> StreamingResponse:
    """RF-V.3 — sintetiza PT-PT → MP3 streaming via ElevenLabs.

    Response é `StreamingResponse` com `media_type=audio/mpeg`; o frontend
    pode fazer pipe directo a `<audio>` / `MediaSource`.

    Respostas:
        - 200 OK: stream MP3 (`audio/mpeg`).
        - 400: texto oversize / voice_id ausente.
        - 401: cookie ausente/inválido.
        - 422: validação Pydantic (text vazio / len > 5000).
        - 502: falha upstream ElevenLabs.
    """
    try:
        result = voice_tts.synthesize(
            req.text,
            voice_id=req.voice_id,
            session_id=x_voice_session_id,
            user_id=str(user["sub"]),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001 — traduzir qualquer erro SDK em 502
        logger.warning(
            "voice.tts.upstream_fail",
            error_type=type(exc).__name__,
            user_sub=user["sub"],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="voice.tts_upstream",
        ) from exc

    audio_bytes: bytes = result["audio_bytes"]
    mime: str = result["mime"]
    logger.info("voice.tts.ok", user_sub=user["sub"], bytes_len=len(audio_bytes))

    def _iter_audio() -> Any:
        # Single-chunk generator — SDK já concatenou o stream no service.
        # Mantemos `StreamingResponse` (vs `Response`) para permitir futuro
        # passthrough de streaming real sem alterar a assinatura.
        yield audio_bytes

    return StreamingResponse(_iter_audio(), media_type=mime)


@router.post("/intent")
def intent(
    req: IntentRequest,
    x_voice_session_id: UUID | None = _SessionIdHeader,
    user: dict[str, Any] = _CurrentUser,
) -> dict[str, Any]:
    """Classify user voice transcript into an intent for Vox routing.

    Returns:
        - 200 OK: `{intent, params, model_ms}`
        - 401: cookie ausente/inválido.
        - 502: falha upstream Groq.
    """
    try:
        result = voice_intent.classify_intent(
            req.transcript,
            req.history,
            session_id=x_voice_session_id,
            user_id=str(user["sub"]),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "voice.intent.upstream_fail",
            error_type=type(exc).__name__,
            user_sub=user["sub"],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="voice.llm_upstream",
        ) from exc
    logger.info("voice.intent.ok", user_sub=user["sub"], intent=result.get("intent"))
    return result


@router.post("/chat")
def chat(
    req: ChatRequest,
    x_voice_session_id: UUID | None = _SessionIdHeader,
    user: dict[str, Any] = _CurrentUser,
) -> dict[str, Any]:
    """Conversational AI response for general/unrecognized intents.

    Uses Groq Llama 3.3 70B to generate a natural, context-aware Vox reply.
    Called when intent classification returns `general`.

    Returns:
        - 200 OK: `{response_text, model_ms}`
        - 401: cookie ausente/inválido.
        - 502: falha upstream Groq.
    """
    try:
        result = voice_llm.chat_response(
            req.transcript,
            req.history,
            session_id=x_voice_session_id,
            user_id=str(user["sub"]),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "voice.chat.upstream_fail",
            error_type=type(exc).__name__,
            user_sub=user["sub"],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="voice.llm_upstream",
        ) from exc
    logger.info("voice.chat.ok", user_sub=user["sub"])
    return result


@router.post("/telemetry", status_code=status.HTTP_204_NO_CONTENT)
async def post_telemetry(
    batch: TelemetryBatch,
    x_voice_session_id: UUID | None = _SessionIdHeader,
    user: dict[str, Any] = _CurrentUser,
) -> None:
    """Fire-and-forget batch of phase timings. Never blocks caller.

    Writes up to 20 phase events to `voice_latency_events` via
    `telemetry.emit_phase` (swallows all DB errors by design).

    Respostas:
        - 204 No Content: batch aceite (mesmo que todos os inserts falhem
          silenciosamente — telemetria nunca bloqueia o caller).
        - 400: header `X-Voice-Session-Id` ausente / UUID inválido.
        - 401: cookie ausente/inválido.
        - 422: validação Pydantic (events > 20 / campos fora dos limites).
    """
    if x_voice_session_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Voice-Session-Id header required",
        )
    for event in batch.events:
        telemetry.emit_phase(
            session_id=x_voice_session_id,
            user_id=str(user["sub"]),
            phase=event.phase,
            ms=event.ms,
            status=event.status,
        )
