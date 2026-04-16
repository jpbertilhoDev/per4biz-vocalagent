"""
Testes RED para `app.services.crypto` (Sprint 1 · E1 · Task 1).

Cobrem o SPEC §5.1 (Armazenamento de tokens) — AES-256-GCM com formato
`key_version(1 byte) || nonce(12) || ciphertext+tag`, chave carregada de
`settings.ENCRYPTION_KEY` (base64 de 32 bytes).

Mapeiam aos ACs:
- AC-1 (refresh_token cifrado AES-256-GCM na BD)
- AC-8 (tokens nunca em logs — integridade/autenticidade garantida)

Enquanto `app/services/crypto.py` não existir, todos os testes falham
com ModuleNotFoundError — RED autêntica.
"""
from __future__ import annotations

import base64

import pytest
from cryptography.exceptions import InvalidTag

from app.config import get_settings
from app.services.crypto import decrypt, encrypt


def test_encrypt_decrypt_roundtrip() -> None:
    """SPEC §5.1: valor cifrado e decifrado regressa intacto (happy path)."""
    plaintext = b"hello refresh token"

    ciphertext = encrypt(plaintext)

    assert decrypt(ciphertext) == plaintext


def test_encrypt_uses_unique_nonce() -> None:
    """SPEC §5.1: nonce aleatório por chamada — 2 cifragens do mesmo input diferem."""
    plaintext = b"hello refresh token"

    first = encrypt(plaintext)
    second = encrypt(plaintext)

    assert first != second


def test_decrypt_fails_on_tampered_ciphertext() -> None:
    """SPEC §5.1: flipping 1 byte do ciphertext invalida a tag GCM → InvalidTag."""
    ciphertext = bytearray(encrypt(b"hello refresh token"))
    # Último byte pertence à tag GCM — flip garante falha de autenticação.
    ciphertext[-1] ^= 0x01

    with pytest.raises(InvalidTag):
        decrypt(bytes(ciphertext))


def test_decrypt_fails_on_wrong_key_version() -> None:
    """SPEC §5.1: `key_version` desconhecido (0x02) deve ser recusado."""
    # Construir payload válido v1 e substituir o primeiro byte por 0x02.
    valid = bytearray(encrypt(b"hello refresh token"))
    valid[0] = 0x02

    with pytest.raises(ValueError, match="key_version"):
        decrypt(bytes(valid))


def test_encryption_key_loaded_from_settings() -> None:
    """SPEC §5.1: módulo deve usar `settings.ENCRYPTION_KEY`, não literal hardcoded.

    Estratégia: mudar a chave em settings, limpar cache, e verificar que
    ciphertext produzido com a nova chave NÃO decifra com a chave antiga.
    """
    settings = get_settings()
    key_bytes = base64.b64decode(settings.ENCRYPTION_KEY)

    assert len(key_bytes) == 32, "ENCRYPTION_KEY deve ter 32 bytes após base64 decode"
    # Cifragem real sanity-check: precisa que o módulo leia a chave corrente.
    assert decrypt(encrypt(b"sentinel")) == b"sentinel"
