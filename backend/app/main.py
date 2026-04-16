"""
Per4Biz FastAPI application entry point.

V1 single-tenant — ver 07-v1-scope/EXECUTION-NOTES.md.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config import get_settings
from app.logging import configure_logging, get_logger
from app.middleware.session import SessionMiddleware
from app.routers import auth as auth_router
from app.routers import emails as emails_router
from app.routers import me as me_router
from app.routers import voice as voice_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hooks. Fail-fast em config ausente."""
    # Configurar structlog ANTES de qualquer `logger.info` — processor
    # `_redact_pii` é last-resort guard contra fuga de PII/tokens em logs.
    configure_logging()
    logger = get_logger(__name__)
    logger.info("app.startup")
    # Pydantic já validou todas as env vars obrigatórias no import.
    # Aqui podemos adicionar health checks de dependências (Supabase, Groq, etc.)
    # quando os services estiverem implementados.
    yield
    logger.info("app.shutdown")
    # Cleanup (quando houver connection pools, workers, etc.)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Per4Biz API",
        version="0.1.0",
        description="Backend do copiloto vocal Per4Biz (V1 single-tenant)",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=None,
    )

    # Session middleware corre ANTES de qualquer router para popular
    # `request.state.current_user`. Em Starlette, middlewares são executados
    # na ordem inversa da adição (LIFO no request, FIFO na response), pelo
    # que adicionamos o SessionMiddleware APÓS o CORS para que o CORS seja
    # o wrapper exterior (trata preflight primeiro).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Internal-Auth"],
    )
    app.add_middleware(SessionMiddleware)

    @app.get("/health")
    async def health(_request: Request) -> dict[str, str]:
        return {"status": "ok", "service": "per4biz-api", "version": "0.1.0"}

    app.include_router(auth_router.router)  # Sprint 1 (E1)
    app.include_router(me_router.router)  # Sprint 1 (E1) — GDPR trilogy
    app.include_router(emails_router.router)  # Sprint 1.x (E2) — Gmail inbox
    app.include_router(voice_router.router)  # Sprint 2 (E4) — voice pipeline
    # Routers seguintes (próximos sprints):
    # app.include_router(accounts.router) # Sprint 4 (E6)

    return app


app = create_app()
