"""Groq Llama 3.3 70B polish service (SPEC §3 RF-V.2 · Sprint 2 · E4 · Task 4).

Wrapper server-side síncrono do Groq Chat Completions. Recebe um transcript
bruto (PT-PT, vindo do STT Whisper v3) mais contexto do email original e
devolve `{polished_text, model_ms}` — resposta educada pronta para o
utilizador rever e confirmar antes do envio.

Regras:
- Tom cordial/profissional PT-PT (nunca PT-BR); system prompt bloqueia drift.
- SDK síncrono (`Groq`): FastAPI TestClient síncrono — ver PLAN §Risks.
- Zero logs de `transcript`, `context.body` ou `polished_text` (tudo PII —
  LOGGING-POLICY.md §4). Log apenas `model_ms` + comprimentos.
- Qualquer exceção do SDK propaga raw; router `/voice/polish` (Task 7+)
  traduz em 502 com `error_code=voice.llm_upstream` (ERROR-MATRIX §voice).
"""

from __future__ import annotations

import time
from typing import Any

from groq import Groq

from app.config import get_settings
from app.logging import get_logger
from app.services.retry import retry_with_backoff

logger = get_logger(__name__)

_HTTP_TIMEOUT = 30.0

# Janela máxima do corpo do email injetada no prompt. Evita estourar o
# context window do Llama e mantém latência previsível (< 1.2s first-token).
_MAX_BODY_CHARS = 2000

_SYSTEM_PROMPT = """És o copiloto vocal do Per4Biz. Transformas transcrições \
de ditado em português (PT-PT) num email de resposta educado, profissional \
e claro.

REGRAS:
- PT-PT (não PT-BR). Nunca usar "você"; preferir forma impessoal ou "tu" \
conforme contexto.
- Manter exatamente a intenção do ditado — não inventes datas, nomes ou \
factos.
- Corrigir gramática e pontuação.
- Tom cordial e profissional (nem formal demais, nem informal demais).
- Estrutura: saudação curta (Olá <nome>, / Caro <nome>,) + corpo 1-3 \
parágrafos + fecho (Cumprimentos, / Com os melhores cumprimentos,) SEM \
assinatura (o frontend adiciona).
- Responder no contexto do email recebido (assunto + from).
- Sem markdown, sem HTML — texto puro.
- Sem inventar email destinatário, CC, assuntos novos.

Se o ditado for ambíguo ou curto demais, produzir melhor tentativa possível \
— não recusar.
"""


def polish_draft(transcript: str, context: dict[str, str]) -> dict[str, Any]:
    """Polir draft de email via Groq Llama 3.3 70B.

    Args:
        transcript: texto bruto do ditado do utilizador (PT-PT).
        context: metadata do email original. Keys esperadas:
            - `from_name` (str): nome do remetente original.
            - `from_email` (str): email do remetente original.
            - `subject` (str): assunto do email original.
            - `body` (str): corpo do email original (trunca a 2000 chars).

    Returns:
        dict com chaves:
            - `polished_text` (str): resposta educada pronta para enviar.
            - `model_ms` (int): latência da chamada ao LLM em milissegundos.

    Raises:
        Exception: qualquer erro do SDK Groq propaga raw (router traduz 502).
    """
    settings = get_settings()
    client = Groq(api_key=settings.GROQ_API_KEY, timeout=_HTTP_TIMEOUT)

    from_name = context.get("from_name") or context.get("from_email", "")
    subject = context.get("subject", "")
    body = context.get("body", "")[:_MAX_BODY_CHARS]

    user_content = (
        f"Email recebido de: {from_name}\n"
        f"Assunto: {subject}\n"
        f"Corpo (primeiros {_MAX_BODY_CHARS} chars):\n{body}\n\n"
        f"---\n\n"
        f"Ditado do utilizador (transcrição):\n{transcript}\n\n"
        f"Gera a resposta em PT-PT."
    )

    t0 = time.monotonic()
    response = retry_with_backoff(
        client.chat.completions.create,
        model=settings.GROQ_LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.5,
        max_tokens=500,
    )
    model_ms = int((time.monotonic() - t0) * 1000)

    polished_text: str = response.choices[0].message.content or ""

    # NOTA: nunca logar `transcript`, `context.body` nem `polished_text`
    # (todos PII — LOGGING-POLICY §4). Apenas métricas numéricas.
    logger.info(
        "voice_llm.polish.ok",
        model_ms=model_ms,
        transcript_len=len(transcript),
        output_len=len(polished_text),
    )

    return {"polished_text": polished_text, "model_ms": model_ms}
