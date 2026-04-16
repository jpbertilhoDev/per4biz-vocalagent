"""
FastAPI dependencies partilhadas (Sprint 1 · E1 · SPEC §5.3).

Exposto:
    - `current_user(request)` — devolve o payload injectado pelo
      `SessionMiddleware` ou levanta `HTTPException(401)`.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status


def current_user(request: Request) -> dict[str, Any]:
    """Devolve o utilizador autenticado ou 401 (AC-6).

    O `SessionMiddleware` é responsável por popular
    `request.state.current_user` com `{sub, email}` quando o cookie
    `__Host-session` é válido. Ausência / invalidez resulta em `None`, que
    aqui convertemos em `HTTPException(401)` sem fornecer pistas sobre o
    motivo (token expirado vs ausente vs adulterado).
    """
    user: dict[str, Any] | None = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user
