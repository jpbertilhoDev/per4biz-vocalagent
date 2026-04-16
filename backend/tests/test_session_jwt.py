"""
Testes RED para `app.services.session_jwt` (Sprint 1 · E1 · Task 5).

Cobrem o SPEC §5.3 (Sessão FastAPI-managed — V1 sem Supabase Auth). O token
é um JWT HS256 assinado com `settings.INTERNAL_API_SHARED_SECRET`, claims
`sub` (user_id), `email`, `iat`, `exp` (TTL 7 dias). `maybe_renew` aplica
renovação rolling: reemite apenas quando falta < 1 dia para expirar.

Mapeiam ao AC-3 (sessão persiste 7 dias; rolling renewal perto da expiração).

Enquanto `app/services/session_jwt.py` não existir, a colecção falha com
ModuleNotFoundError — RED autêntica.
"""
from __future__ import annotations

import time
from uuid import UUID

import pytest
from jose import ExpiredSignatureError, jwt

from app.config import get_settings
from app.services.session_jwt import decode_session, issue_session, maybe_renew


USER_ID = UUID("00000000-0000-0000-0000-000000000001")
EMAIL = "test@per4biz.local"


def test_issue_and_decode_roundtrip() -> None:
    """SPEC §5.3 · AC-3: token emitido por `issue_session` é decodificável.

    O payload devolvido contém `sub` (user_id string), `email`, `iat` e `exp`.
    """
    token = issue_session(USER_ID, EMAIL)

    payload = decode_session(token)

    assert payload["sub"] == str(USER_ID)
    assert payload["email"] == EMAIL
    assert "iat" in payload
    assert "exp" in payload


def test_session_exp_7d() -> None:
    """SPEC §5.3 · AC-3: TTL da sessão é exactamente 7 dias (604800 segundos)."""
    token = issue_session(USER_ID, EMAIL)

    payload = decode_session(token)

    assert payload["exp"] - payload["iat"] == 7 * 86400


def test_decode_rejects_expired() -> None:
    """SPEC §5.3 · AC-3: token com `exp` no passado é rejeitado.

    `decode_session` propaga `ExpiredSignatureError` sem wrapping.
    """
    settings = get_settings()
    expired_token = jwt.encode(
        {"sub": str(USER_ID), "email": EMAIL, "iat": 1, "exp": 2},
        settings.INTERNAL_API_SHARED_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(ExpiredSignatureError):
        decode_session(expired_token)


def test_renew_returns_none_in_stable_window() -> None:
    """SPEC §5.3 · AC-3: token fresco (exp - now ~= 7d) não é reemitido.

    Dentro da janela estável (>1 dia para expirar), `maybe_renew` devolve
    `None` para sinalizar "mantém o token actual".
    """
    token = issue_session(USER_ID, EMAIL)

    assert maybe_renew(token) is None


def test_renew_reissues_near_expiry() -> None:
    """SPEC §5.3 · AC-3: rolling renewal quando falta < 1 dia para expirar.

    Constrói manualmente um token com 1h de vida restante (iat há ~7d-1h)
    e verifica que `maybe_renew` devolve um novo token com `exp` posterior.
    """
    settings = get_settings()
    now = int(time.time())
    iat = now - (7 * 86400) + 3600  # 1h restante até exp
    old_token = jwt.encode(
        {"sub": str(USER_ID), "email": EMAIL, "iat": iat, "exp": iat + 7 * 86400},
        settings.INTERNAL_API_SHARED_SECRET,
        algorithm="HS256",
    )

    new_token = maybe_renew(old_token)

    assert new_token is not None
    assert new_token != old_token
    assert decode_session(new_token)["exp"] > decode_session(old_token)["exp"]
