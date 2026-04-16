"""
Testes RED para `app.services.voice_stt` (Sprint 2 · E4 · Task 1).

Módulo alvo (Task 2 implementa):
    `app.services.voice_stt` — wrapper server-side do Groq Whisper v3.

    Expõe:
        transcribe(audio_bytes: bytes, mime: str = "audio/webm") -> dict[str, Any]
            Retorna: {"text": str, "language": str | None, "duration_ms": int}

ACs preparados:
    - RF-V.1 — `POST /voice/transcribe` multipart audio ≤1MB → Groq Whisper v3
      → `{text, language, duration_ms}` (ver SPEC §3).
    - US-V.2 — Record → Groq Whisper → transcript visível (SPEC §2 / PLAN Task 2).

Limite duro:
    - Max audio size: 1 MB (1_048_576 bytes). Excede → `ValueError` (sem tocar
      na API Groq — fail-fast no call site).

Enquanto `app/services/voice_stt.py` não existir, a colecção falha com
`ModuleNotFoundError: No module named 'app.services.voice_stt'` — RED
autêntica. Após GREEN (Task 2), os 3 testes passam sem alterar este ficheiro.

Flags para o specialist (Task 2):
    - `from groq import Groq` ao nível do módulo (permite
      `mocker.patch("app.services.voice_stt.Groq", ...)`).
    - SDK síncrono: `client = Groq(api_key=settings.GROQ_API_KEY)`
      (FastAPI TestClient é síncrono — PLAN §Risks).
    - Chamada: `client.audio.transcriptions.create(
          file=("audio.webm", audio_bytes, mime),
          model=settings.GROQ_STT_MODEL,
          response_format="verbose_json",
          language="pt",
      )`
      `verbose_json` devolve objeto com `.text`, `.language`, `.duration`
      (segundos, float). Converter `duration_ms = int(duration * 1000)`.
      Se `duration` faltar, devolver `0`.
    - Validar `len(audio_bytes) <= 1_048_576` ANTES de instanciar Groq.
      Excede → `raise ValueError("audio too large: ...")`.
    - Propagar `groq.APIError` raw — router `/voice/transcribe` traduz em 502.
    - **Nunca logar `text`** (transcript = PII). Log apenas `duration_ms` +
      tamanho em bytes (ver LOGGING-POLICY.md).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MAX_AUDIO_BYTES = 1_048_576  # 1 MB — ver SPEC §3 / RF-V.1
FAKE_TRANSCRIPT = "Olá João, recebi a tua mensagem"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_groq_mock(
    *,
    text: str = FAKE_TRANSCRIPT,
    language: str | None = "pt",
    duration_seconds: float | None = 3.2,
) -> MagicMock:
    """Mock do cliente `groq.Groq` com resposta `verbose_json` realista.

    A resposta real do SDK é um objeto (não dict) com atributos
    `.text`, `.language`, `.duration` — ver docs Groq / Whisper.
    """
    client = MagicMock(name="groq_client")
    response = MagicMock(name="transcription_response")
    response.text = text
    response.language = language
    response.duration = duration_seconds
    client.audio.transcriptions.create.return_value = response
    return client


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


def test_transcribe_returns_text_and_duration(mocker: MockerFixture) -> None:
    """RF-V.1 / US-V.2 — sucesso: transcribe retorna dict com text, language, duration_ms.

    Mockamos `groq.Groq` ao nível do módulo `app.services.voice_stt` para que
    a importação real do SDK não toque a rede. A resposta simula o formato
    `verbose_json` (objeto com atributos `.text`, `.language`, `.duration`).
    """
    groq_client = _build_groq_mock(
        text=FAKE_TRANSCRIPT,
        language="pt",
        duration_seconds=3.2,
    )
    groq_ctor = mocker.patch("app.services.voice_stt.Groq", return_value=groq_client)

    from app.services.voice_stt import transcribe

    result: dict[str, Any] = transcribe(b"fake_webm_audio_bytes", "audio/webm")

    # Contrato do retorno
    assert isinstance(result, dict)
    assert "text" in result and isinstance(result["text"], str) and len(result["text"]) > 0
    assert result["text"] == FAKE_TRANSCRIPT
    assert "duration_ms" in result
    assert isinstance(result["duration_ms"], int)
    assert result["duration_ms"] >= 0
    # language pode ser None (Whisper falha a detectar) ou str ISO-639
    assert "language" in result
    assert result["language"] is None or isinstance(result["language"], str)

    # Groq foi instanciado (via settings.GROQ_API_KEY) e chamado uma vez
    assert groq_ctor.called
    groq_client.audio.transcriptions.create.assert_called_once()


def test_rejects_audio_too_large(mocker: MockerFixture) -> None:
    """RF-V.1 — fail-fast: audio > 1 MB deve levantar ValueError sem chamar Groq.

    Regra de custo/latência (LATENCY targets): validar tamanho ANTES de
    instanciar cliente Groq. Isto evita round-trip desperdiçado e pagamento
    de tokens por uploads gigantes vindos do browser.
    """
    groq_ctor = mocker.patch("app.services.voice_stt.Groq")

    big_audio = b"x" * (MAX_AUDIO_BYTES + 1)  # 1 MB + 1 byte

    from app.services.voice_stt import transcribe

    with pytest.raises(ValueError, match=r"(?i)audio too large|too large|size"):
        transcribe(big_audio, "audio/webm")

    # Groq nunca foi tocado — fail-fast antes de instanciar cliente
    assert not groq_ctor.called


def test_handles_groq_api_error(mocker: MockerFixture) -> None:
    """RF-V.1 — erro de upstream: propagar exceção crua para o router traduzir.

    O router `/voice/transcribe` (Task 7) mapeia `groq.APIError` → HTTP 502
    com `error_code=voice.stt_upstream` (ver ERROR-MATRIX.md §voice).
    O serviço em si não deve esconder/wrappar — propaga raw (após retry).
    """
    groq_client = MagicMock(name="groq_client")
    groq_client.audio.transcriptions.create.side_effect = Exception("groq upstream unavailable")
    mocker.patch("app.services.voice_stt.Groq", return_value=groq_client)
    mocker.patch("app.services.retry.time.sleep")  # skip real delays

    from app.services.voice_stt import transcribe

    with pytest.raises(Exception, match=r"groq upstream unavailable"):
        transcribe(b"audio_ok_size", "audio/webm")

    # With retry (max_retries=2), the function is called 3 times total
    assert groq_client.audio.transcriptions.create.call_count == 3
