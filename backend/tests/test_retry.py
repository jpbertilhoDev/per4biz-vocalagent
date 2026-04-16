"""Tests for retry_with_backoff utility."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.retry import retry_with_backoff


def test_retry_success_first_attempt() -> None:
    """Should return result on first try if fn succeeds."""
    fn = MagicMock(return_value="ok")
    result = retry_with_backoff(fn, max_retries=2)
    assert result == "ok"
    assert fn.call_count == 1


def test_retry_success_after_failures() -> None:
    """Should retry and return result on eventual success."""
    fn = MagicMock(side_effect=[RuntimeError("fail1"), RuntimeError("fail2"), "ok"])
    with patch("app.services.retry.time.sleep"):
        result = retry_with_backoff(fn, max_retries=2, base_delay=0.01)
    assert result == "ok"
    assert fn.call_count == 3


def test_retry_exhausted_raises_last() -> None:
    """Should raise last exception after all retries exhausted."""
    fn = MagicMock(side_effect=RuntimeError("always fails"))
    with patch("app.services.retry.time.sleep"):
        with pytest.raises(RuntimeError, match="always fails"):
            retry_with_backoff(fn, max_retries=2, base_delay=0.01)
    assert fn.call_count == 3


def test_retry_does_not_retry_value_error() -> None:
    """ValueError should propagate immediately without retry."""
    fn = MagicMock(side_effect=ValueError("bad input"))
    with pytest.raises(ValueError, match="bad input"):
        retry_with_backoff(fn, max_retries=3)
    assert fn.call_count == 1


def test_retry_passes_args_and_kwargs() -> None:
    """Args and kwargs should be forwarded to fn."""
    fn = MagicMock(return_value="ok")
    retry_with_backoff(fn, "a", "b", key="val", max_retries=0)
    fn.assert_called_once_with("a", "b", key="val")


def test_retry_respects_max_delay() -> None:
    """Delay should be capped at max_delay."""
    fn = MagicMock(side_effect=[RuntimeError("f"), RuntimeError("f"), "ok"])
    with patch("app.services.retry.time.sleep") as mock_sleep:
        retry_with_backoff(fn, max_retries=2, base_delay=10.0, max_delay=2.0)
    # Both delays should be capped at 2.0
    for call in mock_sleep.call_args_list:
        assert call[0][0] <= 2.0


def test_retry_custom_retryable_exceptions() -> None:
    """Only specified exception types should trigger retry."""
    fn = MagicMock(side_effect=TypeError("no retry"))
    with pytest.raises(TypeError, match="no retry"):
        retry_with_backoff(fn, max_retries=2, retryable_exceptions=(RuntimeError,))
    assert fn.call_count == 1
