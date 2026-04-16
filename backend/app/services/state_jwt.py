"""
State JWT — protecção CSRF do fluxo OAuth Google (SPEC §5.2 · AC-7).

Este módulo assina/verifica o parâmetro `state` trocado com o Google durante
o fluxo `/auth/google/start` → `/auth/google/callback`. O token é um JWT
HS256 com TTL de 10 minutos, assinado com `INTERNAL_API_SHARED_SECRET`.

Payload:
    - `nonce` (hex 32 chars, único por chamada)
    - `redirect_to` (caminho pós-login, pass-through)
    - `iat` (issued at, UNIX seconds)
    - `exp` (iat + 600, expiry)

Este módulo não loga tokens nem segredos (LOGGING-POLICY).
"""
from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from jose import jwt

from app.config import get_settings


def sign_state(redirect_to: str) -> str:
    """Gera um state JWT HS256 com TTL 10min (SPEC §5.2 · AC-7).

    `iat` é calculado uma única vez para garantir `exp - iat == 600` exacto
    (evita race entre duas chamadas a `time.time()`).

    Args:
        redirect_to: caminho destino pós-login (pass-through no payload).

    Returns:
        JWT assinado (compact serialization "header.payload.signature").
    """
    settings = get_settings()
    iat = int(time.time())
    payload: dict[str, Any] = {
        "nonce": uuid4().hex,
        "redirect_to": redirect_to,
        "iat": iat,
        "exp": iat + 600,
    }
    return jwt.encode(payload, settings.INTERNAL_API_SHARED_SECRET, algorithm="HS256")


def verify_state(token: str) -> dict[str, Any]:
    """Valida assinatura e expiry de um state JWT (SPEC §5.2 · AC-7).

    Propaga sem wrapping:
        - `jose.ExpiredSignatureError` quando `exp < now`.
        - `jose.JWTError` em tamper, assinatura inválida ou secret errado.

    Args:
        token: JWT compact recebido no callback OAuth.

    Returns:
        Payload decoded com `nonce`, `redirect_to`, `iat`, `exp`.
    """
    settings = get_settings()
    decoded: dict[str, Any] = jwt.decode(
        token, settings.INTERNAL_API_SHARED_SECRET, algorithms=["HS256"]
    )
    return decoded
