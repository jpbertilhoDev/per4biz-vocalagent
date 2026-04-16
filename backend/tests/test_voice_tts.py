"""
Testes RED para `app.services.voice_tts` (Sprint 2 · E4 · Task 5).

Módulo alvo (Task 6 implementa):
    `app.services.voice_tts` — wrapper server-side do ElevenLabs TTS.

    Expõe:
        synthesize(text: str, voice_id: str | None = None) -> dict[str, Any]
            Retorna: {"audio_bytes": bytes, "mime": "audio/mpeg", "tts_ms": int}
            Levanta `ValueError` quando `len(text) > 5000`.

ACs preparados:
    - RF-V.3 — síntese PT-PT com voz feminina via ElevenLabs (SPEC §3 · PLAN Task 5+6).
    - AC-E4.US4 (voice reply playback) — resposta do assistente convertida
      em MP3 streamable para `<audio>` em `audio/mpeg`.

Limite duro:
    - Max text length: 5000 chars. Excede → `ValueError` (fail-fast antes de
      instanciar cliente — evita custo / latência em inputs absurdos).

Enquanto `app/services/voice_tts.py` não existir, a colecção falha com
`ModuleNotFoundError: No module named 'app.services.voice_tts'` — RED
autêntica. Após GREEN (Task 6), os 3 testes passam sem alterar este ficheiro.

Flags para o specialist (Task 6):
    - `from elevenlabs.client import ElevenLabs` ao nível do módulo (permite
      `mocker.patch("app.services.voice_tts.ElevenLabs", ...)`).
    - SDK síncrono: `client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)`
      (FastAPI TestClient é síncrono — PLAN §Risks).
    - Chamada: `stream = client.text_to_speech.convert(
          voice_id=voice_id or settings.ELEVENLABS_VOICE_ID,
          model_id=settings.ELEVENLABS_MODEL_ID,
          text=text,
          output_format="mp3_44100_128",
      )`
      `convert(...)` devolve um iterável/generator de `bytes` (chunks MP3).
      Concatenar com `b"".join(stream)`.
    - `mime` é fixo `"audio/mpeg"` — MP3 por output_format `mp3_*`.
    - Medir latência: `t0 = time.monotonic()` antes da chamada e
      `tts_ms = int((time.monotonic() - t0) * 1000)` após concatenar.
      Sempre `>= 0`.
    - Validar `len(text) <= 5000` ANTES de instanciar `ElevenLabs` — se
      exceder, `raise ValueError("text too long: ...")`. Mock não deve ser
      chamado (fail-fast).
    - Propagar qualquer exceção do SDK raw — router `/voice/tts` (Task 7+)
      traduz em 502 `voice.tts_upstream` (ERROR-MATRIX §voice).
    - **Nunca logar** `text` nem `audio_bytes` (PII — LOGGING-POLICY.md).
      Log apenas `tts_ms` + `text_len` + `bytes_len`.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MAX_TEXT_CHARS = 5000  # SPEC §3 / RF-V.3 — limite duro de input

# Chunks MP3 simulados (bytes arbitrários). Suficientes para validar que o
# serviço concatena na ordem correcta.
FAKE_MP3_CHUNKS: list[bytes] = [b"\xff\xfb", b"\xe4\x64", b"end"]
FAKE_MP3_CONCAT: bytes = b"".join(FAKE_MP3_CHUNKS)  # b"\xff\xfb\xe4\x64end"

DEFAULT_VOICE_ID = "XrExE9yKIg1WjnnlVkGX"  # definido em conftest / settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_elevenlabs_mock(
    *,
    chunks: list[bytes] | None = None,
) -> MagicMock:
    """Mock do cliente `elevenlabs.client.ElevenLabs`.

    `client.text_to_speech.convert(...)` devolve um iterável de `bytes`
    (generator real do SDK). Usamos `iter([...])` para simular consumo
    one-shot — se o serviço tentar iterar duas vezes, falha.
    """
    client = MagicMock(name="elevenlabs_client")
    payload = chunks if chunks is not None else FAKE_MP3_CHUNKS
    client.text_to_speech.convert.return_value = iter(payload)
    return client


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


def test_tts_returns_audio_bytes_and_mime(mocker: MockerFixture) -> None:
    """RF-V.3 — sucesso: synthesize retorna audio_bytes concatenado + mime mpeg.

    Mockamos `elevenlabs.client.ElevenLabs` ao nível do módulo
    `app.services.voice_tts` para que o import real do SDK não toque a rede.
    A resposta simula o stream de chunks MP3 devolvido por `text_to_speech
    .convert(...)`. Validamos contrato de retorno: bytes concatenados (ordem
    preservada), `mime == "audio/mpeg"`, `tts_ms >= 0`.
    """
    client = _build_elevenlabs_mock(chunks=FAKE_MP3_CHUNKS)
    eleven_ctor = mocker.patch("app.services.voice_tts.ElevenLabs", return_value=client)

    from app.services.voice_tts import synthesize

    result: dict[str, Any] = synthesize("Olá JP")

    # Contrato do retorno
    assert isinstance(result, dict)
    assert "audio_bytes" in result
    assert isinstance(result["audio_bytes"], bytes)
    assert result["audio_bytes"] == FAKE_MP3_CONCAT, (
        "audio_bytes deve ser a concatenação ordenada dos chunks do stream"
    )
    assert len(result["audio_bytes"]) > 0

    # MIME fixo — ElevenLabs output_format `mp3_*` sempre devolve audio/mpeg
    assert result["mime"] == "audio/mpeg"

    # Latência reportada e não-negativa
    assert "tts_ms" in result
    assert isinstance(result["tts_ms"], int)
    assert result["tts_ms"] >= 0

    # ElevenLabs foi instanciado (via settings.ELEVENLABS_API_KEY) e chamado 1x
    assert eleven_ctor.called
    client.text_to_speech.convert.assert_called_once()


def test_tts_uses_default_voice_id_from_settings(mocker: MockerFixture) -> None:
    """RF-V.3 — quando `voice_id` não é passado, usa `ELEVENLABS_VOICE_ID` das settings.

    Sem argumento, o serviço tem de ler do `get_settings().ELEVENLABS_VOICE_ID`
    (conftest fixa `"XrExE9yKIg1WjnnlVkGX"`). Inspeccionamos a chamada ao SDK
    e exigimos que o voice ID de referência apareça em kwargs OU num dos
    positional args. Isto evita hard-code acidental dentro do serviço.
    """
    client = _build_elevenlabs_mock()
    mocker.patch("app.services.voice_tts.ElevenLabs", return_value=client)

    from app.services.voice_tts import synthesize

    synthesize("texto qualquer")

    call = client.text_to_speech.convert.call_args
    assert call is not None, "text_to_speech.convert nunca foi chamado"

    # Coletamos todos os valores passados (kwargs + args) numa tupla única
    # para um assert resiliente — SDK pode mudar entre kwarg-only e posicional.
    values = tuple(call.args) + tuple(call.kwargs.values())
    assert DEFAULT_VOICE_ID in values, (
        f"voice_id default '{DEFAULT_VOICE_ID}' não foi passado a "
        f"text_to_speech.convert; args={call.args}, kwargs={call.kwargs}"
    )


def test_tts_rejects_text_too_long(mocker: MockerFixture) -> None:
    """RF-V.3 — fail-fast: `len(text) > 5000` deve levantar ValueError sem chamar ElevenLabs.

    Regra de custo/latência: validar tamanho ANTES de instanciar o cliente.
    Isto evita round-trip desperdiçado e pagamento de créditos de caracteres
    em inputs absurdos (ex: ataque de amplificação ou bug de UI a enviar
    draft completo).
    """
    eleven_ctor = mocker.patch("app.services.voice_tts.ElevenLabs")

    big = "x" * (MAX_TEXT_CHARS + 1)  # 5001 chars

    from app.services.voice_tts import synthesize

    with pytest.raises(ValueError, match=r"(?i)text too long|too long|length"):
        synthesize(big)

    # ElevenLabs nunca foi tocado — fail-fast antes de instanciar cliente
    assert not eleven_ctor.called
