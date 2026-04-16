"""Shared pytest fixtures for Per4Biz backend."""

import os

import pytest
from fastapi.testclient import TestClient


def _set_test_env() -> None:
    """Minimum env vars needed for app boot during tests."""
    defaults = {
        "ENVIRONMENT": "development",
        "ALLOWED_USER_EMAIL": "test@per4biz.local",
        "USER_ID": "00000000-0000-0000-0000-000000000001",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role",
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REDIRECT_URI": "http://localhost:8000/auth/google/callback",
        "GROQ_API_KEY": "test-groq-key",
        "ELEVENLABS_API_KEY": "test-elevenlabs-key",
        # Voice ID público de referência (Sprint 2 · E4 · Task 5/6). Conftest
        # define-o mesmo sendo opcional em Settings, para que testes de
        # `voice_tts` possam inspecionar o kwarg sem depender de .env real.
        "ELEVENLABS_VOICE_ID": "XrExE9yKIg1WjnnlVkGX",
        # base64(b"x" * 32) — decodes to exactly 32 bytes (AES-256 key size).
        # Deterministic for reproducible tests; replace before prod.
        "ENCRYPTION_KEY": "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg=",  # noqa: S105
        "INTERNAL_API_SHARED_SECRET": "test-internal-secret",  # noqa: S105
    }
    for k, v in defaults.items():
        os.environ.setdefault(k, v)


_set_test_env()


@pytest.fixture
def client() -> TestClient:
    """Synchronous TestClient wrapping the FastAPI app."""
    # Import AFTER env is set so Settings() succeeds.
    from app.main import app

    return TestClient(app)
