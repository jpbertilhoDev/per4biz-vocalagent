"""
Serviço de cifra AES-256-GCM para tokens Google (SPEC §5.1).

Formato do ciphertext:
    byte[0]     = key_version (atualmente `settings.ENCRYPTION_KEY_VERSION`, 0x01)
    byte[1:13]  = nonce GCM de 12 bytes (aleatório por chamada)
    byte[13:]   = AESGCM(key).encrypt(...) — inclui ciphertext + tag GCM de 16 bytes

A chave AES-256 (32 bytes) é obtida via `base64.b64decode(settings.ENCRYPTION_KEY)`.
Nunca escreve plaintext, ciphertext nem chaves em logs (silêncio absoluto).
"""
from __future__ import annotations

import base64
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings

_NONCE_SIZE = 12


def _get_key() -> bytes:
    """Carrega a chave AES-256 (32 bytes) a partir de `settings.ENCRYPTION_KEY` (base64)."""
    settings = get_settings()
    return base64.b64decode(settings.ENCRYPTION_KEY)


def encrypt(plaintext: bytes) -> bytes:
    """Cifra `plaintext` em AES-256-GCM com nonce novo (SPEC §5.1).

    Retorna `key_version(1) || nonce(12) || ciphertext+tag`.
    """
    settings = get_settings()
    key = _get_key()
    nonce = secrets.token_bytes(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    return bytes([settings.ENCRYPTION_KEY_VERSION]) + nonce + ct_with_tag


def decrypt(ciphertext: bytes) -> bytes:
    """Decifra payload produzido por `encrypt` (SPEC §5.1).

    Levanta `ValueError` se `key_version` não for suportada e `InvalidTag`
    (via `cryptography`) se a autenticidade do ciphertext falhar.
    """
    settings = get_settings()
    version = ciphertext[0]
    if version != settings.ENCRYPTION_KEY_VERSION:
        raise ValueError(f"unsupported key_version: {version}")
    nonce = ciphertext[1 : 1 + _NONCE_SIZE]
    ct_with_tag = ciphertext[1 + _NONCE_SIZE :]
    aesgcm = AESGCM(_get_key())
    return aesgcm.decrypt(nonce, ct_with_tag, None)
