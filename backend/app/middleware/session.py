"""
SessionMiddleware — lê cookie `__Host-session`, injecta `current_user` em
`request.state`, aplica rolling renewal (SPEC §5.3 · AC-3/AC-6).

Comportamento:
    - Cookie ausente / inválido / expirado → `request.state.current_user = None`
      (a dependency `current_user` levanta 401 downstream).
    - Cookie válido → `request.state.current_user = {sub, email}` e, se
      `maybe_renew` devolver token novo (janela <1d), anexa `Set-Cookie` à
      response.

Invariantes LOGGING-POLICY:
    - Nunca logar o token, email ou qualquer fragmento do payload.
    - Apenas eventos sem PII (`session.invalid_cookie`).
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from jose import ExpiredSignatureError, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging import get_logger
from app.services.session_jwt import decode_session, maybe_renew

SESSION_COOKIE = "__Host-session"
_MAX_AGE_SECONDS = 7 * 86400

logger = get_logger(__name__)


class SessionMiddleware(BaseHTTPMiddleware):
    """Lê/valida o cookie de sessão e aplica rolling renewal."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.current_user = None
        renewed: str | None = None

        token = request.cookies.get(SESSION_COOKIE)
        if token:
            try:
                payload = decode_session(token)
                request.state.current_user = {
                    "sub": payload["sub"],
                    "email": payload["email"],
                }
                renewed = maybe_renew(token)
            except (ExpiredSignatureError, JWTError):
                # Zero PII — apenas sinal de cookie inválido.
                logger.info("session.invalid_cookie")
                request.state.current_user = None
                renewed = None

        response = await call_next(request)

        if renewed is not None:
            response.set_cookie(
                key=SESSION_COOKIE,
                value=renewed,
                httponly=True,
                secure=True,
                samesite="none",
                path="/",
                max_age=_MAX_AGE_SECONDS,
            )
        return response
