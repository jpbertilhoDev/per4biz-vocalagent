"""
Testes RED para `app.services.state_jwt` (Sprint 1 · E1 · Task 3).

Cobrem o SPEC §5.2 (State JWT CSRF protection) — HS256 assinado com
`settings.INTERNAL_API_SHARED_SECRET`, payload com `nonce`, `redirect_to`,
`iat`, `exp` (TTL 10 minutos).

Mapeiam ao AC-7 (protecção CSRF: state inválido/expirado/adulterado → 400).

Enquanto `app/services/state_jwt.py` não existir, a colecção falha com
ModuleNotFoundError — RED autêntica.
"""
from __future__ import annotations

import time

import pytest
from jose import ExpiredSignatureError, JWTError, jwt

from app.config import get_settings
from app.services.state_jwt import sign_state, verify_state


def test_sign_and_verify_roundtrip() -> None:
    """SPEC §5.2: token válido gerado por `sign_state` é aceite por `verify_state`.

    Payload devolvido contém `nonce`, `redirect_to`, `iat`, `exp`.
    """
    token = sign_state(redirect_to="/inbox")

    payload = verify_state(token)

    assert payload["redirect_to"] == "/inbox"
    assert isinstance(payload["nonce"], str) and payload["nonce"] != ""
    assert "iat" in payload
    assert "exp" in payload


def test_verify_fails_on_tamper() -> None:
    """SPEC §5.2 · AC-7: alterar 1 char do segmento payload invalida a assinatura."""
    token = sign_state(redirect_to="/inbox")
    header, body, signature = token.split(".")
    # Flip 1 char do meio do payload base64url — a assinatura deixa de bater.
    mid = len(body) // 2
    tampered_char = "A" if body[mid] != "A" else "B"
    tampered_body = body[:mid] + tampered_char + body[mid + 1 :]
    tampered = f"{header}.{tampered_body}.{signature}"

    with pytest.raises(JWTError):
        verify_state(tampered)


def test_verify_fails_on_expired() -> None:
    """SPEC §5.2 · AC-7: token com `exp` no passado é recusado com ExpiredSignatureError."""
    settings = get_settings()
    # Construção manual de um JWT já expirado (exp = 1 → 1970-01-01T00:00:01Z).
    expired_token = jwt.encode(
        {"nonce": "deadbeef", "redirect_to": "/inbox", "iat": 1, "exp": 1},
        settings.INTERNAL_API_SHARED_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(ExpiredSignatureError):
        verify_state(expired_token)


def test_verify_fails_on_wrong_secret() -> None:
    """SPEC §5.2 · AC-7: token assinado com secret diferente é rejeitado."""
    now = int(time.time())
    foreign_token = jwt.encode(
        {"nonce": "deadbeef", "redirect_to": "/inbox", "iat": now, "exp": now + 600},
        "outro-secret-completamente-diferente",
        algorithm="HS256",
    )

    with pytest.raises(JWTError):
        verify_state(foreign_token)


def test_sign_sets_exp_10min() -> None:
    """SPEC §5.2: TTL do state JWT é exactamente 10 minutos (600 segundos)."""
    token = sign_state(redirect_to="/inbox")

    payload = verify_state(token)

    assert payload["exp"] - payload["iat"] == 600
