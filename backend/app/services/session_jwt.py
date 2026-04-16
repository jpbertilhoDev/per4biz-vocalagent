"""
Session JWT — sessão FastAPI-managed em V1 (SPEC §5.3 · AC-3).

V1 não usa Supabase Auth: a sessão do utilizador é um JWT HS256 assinado
com `INTERNAL_API_SHARED_SECRET`, entregue em cookie `__Host-per4biz_session`
(HttpOnly, Secure, SameSite=Lax) pelo callback OAuth. TTL de 7 dias com
renovação rolling quando falta menos de 1 dia para expirar.

Payload:
    - `sub` (user_id UUID como string)
    - `email` (email Google autorizado, igual a `ALLOWED_USER_EMAIL` em V1)
    - `iat` (issued at, UNIX seconds)
    - `exp` (iat + 604800 = 7 dias)

Este módulo não loga tokens, segredos nem emails (LOGGING-POLICY).
"""
from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from jose import jwt

from app.config import get_settings


def issue_session(user_id: UUID, email: str) -> str:
    """Emite um session JWT HS256 com TTL 7 dias (SPEC §5.3 · AC-3).

    `iat` é calculado uma única vez para garantir `exp - iat == 604800`
    exacto (evita race entre chamadas a `time.time()`).

    Args:
        user_id: UUID do utilizador (hardcoded ao `USER_ID` em V1 single-tenant).
        email: email Google autorizado (igual a `ALLOWED_USER_EMAIL` em V1).

    Returns:
        JWT compact serialization "header.payload.signature".
    """
    settings = get_settings()
    iat = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": iat,
        "exp": iat + 7 * 86400,
    }
    return jwt.encode(payload, settings.INTERNAL_API_SHARED_SECRET, algorithm="HS256")


def decode_session(token: str) -> dict[str, Any]:
    """Valida assinatura e expiry de um session JWT (SPEC §5.3 · AC-3).

    Propaga sem wrapping:
        - `jose.ExpiredSignatureError` quando `exp < now`.
        - `jose.JWTError` em tamper, assinatura inválida ou secret errado.

    O middleware upstream é responsável por capturar estas excepções e
    invalidar o cookie forçando re-login.

    Args:
        token: JWT compact recebido no cookie de sessão.

    Returns:
        Payload decoded com `sub`, `email`, `iat`, `exp`.
    """
    settings = get_settings()
    decoded: dict[str, Any] = jwt.decode(
        token, settings.INTERNAL_API_SHARED_SECRET, algorithms=["HS256"]
    )
    return decoded


def maybe_renew(token: str) -> str | None:
    """Rolling renewal: reemite apenas se falta < 1 dia para expirar (AC-3).

    Dentro da janela estável (> 1 dia restante) devolve `None` sinalizando
    "mantém o token actual" — evita reemissão desnecessária em cada request.

    Se `token` já estiver expirado ou inválido, `decode_session` propaga
    `ExpiredSignatureError` / `JWTError` sem captura — o middleware trata
    a re-autenticação.

    Args:
        token: session JWT actual do cookie.

    Returns:
        Novo token quando renovado, ou `None` se dentro da janela estável.
    """
    payload = decode_session(token)
    remaining = int(payload["exp"]) - int(time.time())
    if remaining < 86400:
        return issue_session(UUID(payload["sub"]), payload["email"])
    return None
