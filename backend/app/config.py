"""
Configurações Per4Biz backend — Pydantic Settings.

Lê do ambiente (.env em dev, secrets em Fly.io).
Ver 07-v1-scope/EXECUTION-NOTES.md §4 para o que é obrigatório em V1.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Variáveis de ambiente. Fail-fast se falta algo crítico."""

    model_config = SettingsConfigDict(
        env_file=(_PROJECT_ROOT / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- Environment ---
    ENVIRONMENT: Literal["development", "preview", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- V1 single-tenant gating ---
    ALLOWED_USER_EMAIL: str = Field(..., description="Email Google único autorizado")
    USER_ID: str = Field(..., description="UUID fixo para coluna user_id")

    # --- Supabase (DB + Storage only em V1) ---
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # --- Groq (STT + LLM) ---
    GROQ_API_KEY: str
    GROQ_STT_MODEL: str = "whisper-large-v3"
    GROQ_LLM_MODEL: str = "llama-3.3-70b-versatile"

    # --- ElevenLabs (TTS) ---
    ELEVENLABS_API_KEY: str
    ELEVENLABS_VOICE_ID: str = "XrExE9yKIg1WjnnlVkGX"
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"

    # --- Encryption (AES-256-GCM) ---
    ENCRYPTION_KEY: str = Field(..., description="base64(32 bytes) — usar secrets.token_bytes(32)")
    ENCRYPTION_KEY_VERSION: int = 1

    # --- Internal auth BFF ↔ FastAPI ---
    INTERNAL_API_SHARED_SECRET: str

    # --- Frontend URLs (para CORS) ---
    NEXT_PUBLIC_APP_URL: str = "http://localhost:3000"

    # --- Rate limits (hard-coded em V1) ---
    RATE_LIMIT_VOICE_INTERACTIONS_PER_DAY: int = 200
    RATE_LIMIT_EMAILS_SEND_PER_DAY: int = 100

    # --- Feature flags ---
    FEATURE_VOICE_AGENT_ENABLED: bool = True
    FEATURE_MULTI_ACCOUNT_ENABLED: bool = False
    FEATURE_PUSH_NOTIFICATIONS_ENABLED: bool = False
    FEATURE_CALENDAR_ENABLED: bool = True
    FEATURE_CONTACTS_ENABLED: bool = True
    FEATURE_TRANSCRIPT_RETENTION: bool = False

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.NEXT_PUBLIC_APP_URL]
        if self.ENVIRONMENT == "development":
            origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])
        return origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
