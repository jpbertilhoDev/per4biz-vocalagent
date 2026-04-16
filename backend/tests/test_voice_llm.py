"""
Testes RED para `app.services.voice_llm` (Sprint 2 · E4 · Task 3).

Módulo alvo (Task 4 implementa):
    `app.services.voice_llm` — wrapper server-side do Groq LLM (Llama 3.3 70B)
    para transformar transcripts brutos em emails educados PT-PT.

    Expõe:
        polish_draft(transcript: str, context: dict[str, str]) -> dict[str, Any]
            `context` keys: `from_name`, `from_email`, `subject`, `body`.
            Retorna: {"polished_text": str, "model_ms": int}

ACs preparados:
    - RF-V.2 — polish de draft de email em PT-PT com contexto do email original
      (SPEC §3 · PLAN Task 3+4).
    - AC-E4.US3 (pipeline vocal → email polido) — transcript + contexto → draft
      educado pronto para confirmação do utilizador.

Enquanto `app/services/voice_llm.py` não existir, a colecção falha com
`ModuleNotFoundError: No module named 'app.services.voice_llm'` — RED
autêntica. Após GREEN (Task 4), os 3 testes passam sem alterar este ficheiro.

Flags para o specialist (Task 4):
    - `from groq import Groq` ao nível do módulo (permite
      `mocker.patch("app.services.voice_llm.Groq", ...)`).
    - SDK síncrono: `client = Groq(api_key=settings.GROQ_API_KEY)`.
    - Chamada: `client.chat.completions.create(
          model=settings.GROQ_LLM_MODEL,
          messages=[{"role": "system", ...}, {"role": "user", ...}],
          ...
      )`
    - Injetar `context["from_name"]`, `context["subject"]`, `context["body"]`
      (e opcionalmente `from_email`) nos `messages` para que o LLM tenha o
      contexto do email original. Exigência de teste: pelo menos `from_name`
      ou `subject` deve aparecer literalmente em algum `content` das messages.
    - Medir latência: `t0 = time.monotonic()` antes do `create(...)` e
      `model_ms = int((time.monotonic() - t0) * 1000)` após. Sempre `>= 0`.
    - Ler resposta: `response.choices[0].message.content` (str não vazia).
    - Propagar qualquer exceção do SDK raw — router `/voice/polish` (Task 7+)
      traduz em 502 `voice.llm_upstream` (ERROR-MATRIX §voice).
    - **Nunca logar** `transcript`, `context["body"]` nem `polished_text`
      (tudo PII — LOGGING-POLICY.md). Log apenas `model_ms` + flags
      de comprimento se necessário.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Constantes / fixtures inline
# ---------------------------------------------------------------------------

FAKE_POLISHED = "Caro João,\n\nConfirmo a reunião de terça às 15h.\n\nCumprimentos"

TRANSCRIPT = "responde ao joão a confirmar a reunião terça 15h"

CONTEXT: dict[str, str] = {
    "from_name": "João Silva",
    "from_email": "joao@ex.com",
    "subject": "Reunião",
    "body": "Podemos marcar terça?",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_groq_llm_mock(*, content: str = FAKE_POLISHED) -> MagicMock:
    """Mock do cliente `groq.Groq` com resposta `chat.completions.create`.

    Formato real SDK: `response.choices[0].message.content` (str).
    """
    client = MagicMock(name="groq_llm_client")
    response = MagicMock(name="chat_completion_response")
    choice = MagicMock(name="choice")
    choice.message = MagicMock(name="message")
    choice.message.content = content
    response.choices = [choice]
    client.chat.completions.create.return_value = response
    return client


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


def test_polish_returns_polished_text_and_ms(mocker: MockerFixture) -> None:
    """RF-V.2 — sucesso: polish_draft retorna dict com polished_text + model_ms.

    Mockamos `groq.Groq` ao nível do módulo para evitar rede. O LLM devolve
    um texto PT-PT curto simulando a reescrita pedida. Validamos o contrato
    de retorno (tipos + não-vazio) sem assumir o valor exacto do texto
    (isso é teste de prompting, não de serviço).
    """
    groq_client = _build_groq_llm_mock(content=FAKE_POLISHED)
    groq_ctor = mocker.patch("app.services.voice_llm.Groq", return_value=groq_client)

    from app.services.voice_llm import polish_draft

    result: dict[str, Any] = polish_draft(TRANSCRIPT, CONTEXT)

    # Contrato do retorno
    assert isinstance(result, dict)
    assert "polished_text" in result
    assert isinstance(result["polished_text"], str)
    assert len(result["polished_text"]) > 0
    assert "model_ms" in result
    assert isinstance(result["model_ms"], int)
    assert result["model_ms"] >= 0

    # Groq foi instanciado (via settings.GROQ_API_KEY) e chamado uma vez
    assert groq_ctor.called
    groq_client.chat.completions.create.assert_called_once()


def test_polish_uses_email_context_in_prompt(mocker: MockerFixture) -> None:
    """RF-V.2 — contexto do email deve ser injetado no prompt do LLM.

    O polish tem de "saber" a quem responde e sobre o quê. Inspeccionamos
    os kwargs passados a `chat.completions.create` e exigimos que pelo
    menos `from_name` ("João Silva") ou `subject` ("Reunião") apareça
    literalmente em algum `content` das `messages` (system ou user).

    Também validamos estrutura mínima: `messages` é lista com >= 2 entradas
    e inclui role `system` e role `user`.
    """
    groq_client = _build_groq_llm_mock(content=FAKE_POLISHED)
    mocker.patch("app.services.voice_llm.Groq", return_value=groq_client)

    from app.services.voice_llm import polish_draft

    polish_draft(TRANSCRIPT, CONTEXT)

    # Capturar kwargs da chamada ao SDK
    call = groq_client.chat.completions.create.call_args
    assert call is not None, "chat.completions.create nunca foi chamado"
    kwargs = call.kwargs

    assert "messages" in kwargs, "messages kwarg em falta na chamada ao LLM"
    messages = kwargs["messages"]
    assert isinstance(messages, list)
    assert len(messages) >= 2, "prompt deve ter pelo menos system + user"

    roles = {m.get("role") for m in messages if isinstance(m, dict)}
    assert "system" in roles, "prompt deve incluir role=system"
    assert "user" in roles, "prompt deve incluir role=user"

    # Contexto injetado — pelo menos from_name ou subject deve aparecer
    concat = "\n".join(str(m.get("content", "")) for m in messages if isinstance(m, dict))
    assert ("João Silva" in concat) or ("Reunião" in concat), (
        "prompt não injeta from_name nem subject — contexto do email perdido"
    )


def test_polish_handles_groq_error(mocker: MockerFixture) -> None:
    """RF-V.2 — erro de upstream: propagar exceção raw para o router traduzir.

    O router `/voice/polish` (Task 7+) mapeia qualquer exceção do SDK em
    HTTP 502 com `error_code=voice.llm_upstream` (ERROR-MATRIX §voice).
    O serviço em si propaga sem wrappar (após retry attempts).
    """
    groq_client = MagicMock(name="groq_llm_client")
    groq_client.chat.completions.create.side_effect = Exception("rate limit")
    mocker.patch("app.services.voice_llm.Groq", return_value=groq_client)
    mocker.patch("app.services.retry.time.sleep")  # skip real delays

    from app.services.voice_llm import polish_draft

    with pytest.raises(Exception, match=r"rate limit"):
        polish_draft(TRANSCRIPT, CONTEXT)

    # With retry (max_retries=2), the function is called 3 times total
    assert groq_client.chat.completions.create.call_count == 3
