"""Retry with exponential backoff for upstream API calls.

Provides a simple synchronous retry wrapper for use in service modules
(STT, LLM, TTS, Gmail, Calendar, Contacts). Transient errors (5xx,
rate limits, network timeouts) are retried with exponential backoff.
Non-retryable errors (4xx client errors, ValueErrors) propagate immediately.
"""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

from app.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

_DEFAULT_MAX_RETRIES = 2
_DEFAULT_BASE_DELAY = 1.0
_DEFAULT_MAX_DELAY = 8.0
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def retry_with_backoff(
    fn: Callable[..., T],
    *args: Any,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay: float = _DEFAULT_BASE_DELAY,
    max_delay: float = _DEFAULT_MAX_DELAY,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
    **kwargs: Any,
) -> T:
    """Call `fn(*args, **kwargs)` with exponential backoff on failure.

    Args:
        fn: Callable to execute.
        *args: Positional args passed to fn.
        max_retries: Maximum number of retries (default 2 = 3 total attempts).
        base_delay: Initial delay in seconds (default 1.0).
        max_delay: Maximum delay cap in seconds (default 8.0).
        retryable_exceptions: Exception types that trigger retry.
            If None, retries on all Exception subclasses except ValueError.
        **kwargs: Keyword args passed to fn.

    Returns:
        The return value of fn.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc

            if retryable_exceptions is not None:
                if not isinstance(exc, retryable_exceptions):
                    raise
            else:
                if isinstance(exc, ValueError):
                    raise

            if attempt >= max_retries:
                raise

            delay = min(base_delay * (2**attempt), max_delay)
            logger.warning(
                "retry.attempt",
                fn_name=getattr(fn, "__name__", "unknown"),
                attempt=attempt + 1,
                max_retries=max_retries,
                delay_ms=int(delay * 1000),
                error_type=type(exc).__name__,
            )
            time.sleep(delay)

    raise last_exc  # type: ignore[misc]
