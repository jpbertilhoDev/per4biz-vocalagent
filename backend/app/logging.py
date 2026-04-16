"""
Structured logging com redacção automática de PII — Per4Biz.

Sprint 1 · E1 · Task 9 · LOGGING-POLICY.md §4.

Exposto:
    - `configure_logging()` — chama uma única vez no startup (lifespan).
    - `get_logger(name)` — factory para loggers `structlog.BoundLogger`.
    - `_redact_pii(logger, method_name, event_dict)` — processor usado pela
      chain; exportado com underscore para permitir testes unitários.

Redacção:
    - Keys sensíveis (regex case-insensitive `(token|secret|key|authorization|
      password|refresh|access|code)`) → value substituído por "***".
    - Values string contendo padrão de email → "***@***".
    - Ambas as regras aplicam-se recursivamente em dicts aninhados.
    - Eventos/keys benignos (status_code, user_id UUID, latency_ms) passam
      intactos — nenhum whitelist necessário (a heurística não falsea).

Output:
    - `ENVIRONMENT == "production"` → JSON renderer (Axiom-friendly).
    - caso contrário → ConsoleRenderer colorido (dev ergonomics).
"""
from __future__ import annotations

import logging
import re
import sys
from typing import Any, cast

import structlog
from structlog.stdlib import BoundLogger
from structlog.types import EventDict, Processor, WrappedLogger

from app.config import get_settings

# ---------------------------------------------------------------------------
# Redacção — regexes
# ---------------------------------------------------------------------------

# Termos sensíveis cujo valor é sempre ocultado.
# Match via segmentação da key em "palavras" (split por `_`, `-`, camelCase)
# e comparação contra este set — evita falsos positivos em keys benignas
# como `status_code`, `gmail_message_id`, `user_id`.
_SENSITIVE_TERMS: frozenset[str] = frozenset(
    {
        "token",
        "secret",
        "authorization",
        "password",
        "passwd",
        "refresh",
        "access",
        "apikey",
        "api_key",
        "credential",
        "credentials",
        "cookie",
        "session",
    }
)

# Termos ambíguos (estão dentro de keys benignas) — só matcham se forem
# a PRIMEIRA ou ÚNICA "palavra" da key. Ex: `code` match em `code` / `code_verifier`
# / `auth_code` mas NÃO em `status_code` / `error_code`.
_SENSITIVE_AMBIGUOUS: frozenset[str] = frozenset({"code", "key"})

# Separador para partir keys em palavras — lida com snake_case, kebab-case e
# camelCase (convertido para snake antes do split).
_CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")
_SPLIT_RE = re.compile(r"[_\-\s]+")

# Padrão genérico de email — aplica-se apenas a VALUES (nunca a keys).
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.\w+")

_REDACTED = "***"
_REDACTED_EMAIL = "***@***"


def _redact_value(value: Any) -> Any:
    """Redacta recursivamente um único value.

    - dict → recurse
    - list/tuple → map recursivo
    - str → aplica email regex
    - outros tipos (int, bool, UUID, None) → intactos
    """
    if isinstance(value, dict):
        return {k: _process_pair(k, v) for k, v in cast(dict[str, Any], value).items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(v) for v in value)
    if isinstance(value, str):
        return _EMAIL_RE.sub(_REDACTED_EMAIL, value)
    return value


def _is_sensitive_key(key: str) -> bool:
    """Classifica uma key como sensível.

    Passos:
        1. Normaliza camelCase → snake_case.
        2. Parte em palavras por `_`, `-`, whitespace.
        3. True se QUALQUER palavra bater `_SENSITIVE_TERMS` ou se a
           PRIMEIRA palavra bater `_SENSITIVE_AMBIGUOUS` (ex: `code`/`key`
           standalone mas não como sufixo em `status_code`).
    """
    if not isinstance(key, str) or not key:
        return False
    snake = _CAMEL_RE.sub(r"\1_\2", key).lower()
    parts = [p for p in _SPLIT_RE.split(snake) if p]
    if not parts:
        return False
    if any(p in _SENSITIVE_TERMS for p in parts):
        return True
    # Ambíguos: só matcham se forem a PRIMEIRA palavra.
    # Ex: "code" ✅, "code_verifier" ✅, "auth_code" ❌ (auth não é sensível)
    #     "status_code" ❌ (primeira palavra é "status", ambíguo só no pos 0)
    # Nota: `auth_code` não é capturado aqui, mas "authorization" + "auth" são
    # cobertos pelo set principal; o plan frisa `code` standalone para o
    # authorization_code do OAuth — esse vem sempre como `code` puro no router.
    return parts[0] in _SENSITIVE_AMBIGUOUS


def _process_pair(key: str, value: Any) -> Any:
    """Decide redacção de um par (key, value).

    Se `_is_sensitive_key(key)` → "***".
    Caso contrário aplica redacção ao value (recursiva + email regex).
    """
    if _is_sensitive_key(key):
        return _REDACTED
    return _redact_value(value)


def _redact_pii(
    _logger: WrappedLogger | None,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Processor structlog — redacta PII antes do renderer final.

    Assinatura conforme `structlog.types.Processor`. `_logger` e `_method_name`
    são ignorados; toda a mutação ocorre em `event_dict`.
    """
    return {k: _process_pair(k, v) for k, v in event_dict.items()}


# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------


def configure_logging() -> None:
    """Configura structlog + stdlib logging globalmente.

    Chamar exactamente uma vez no startup (lifespan da FastAPI). Lê
    `settings.ENVIRONMENT` e `settings.LOG_LEVEL` para decidir renderer
    e nível mínimo.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    # Stdlib root handler — structlog delega aqui no final.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,  # sobrepõe qualquer config anterior (ex: uvicorn default)
    )

    renderer: Processor
    if settings.ENVIRONMENT == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _redact_pii,  # guard preventivo — ÚLTIMO antes do renderer
        renderer,
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BoundLogger:
    """Factory de loggers structlog bound.

    Uso:
        from app.logging import get_logger
        logger = get_logger(__name__)
        logger.info("event_name", user_id=..., status_code=200)
    """
    return cast(BoundLogger, structlog.get_logger(name))
