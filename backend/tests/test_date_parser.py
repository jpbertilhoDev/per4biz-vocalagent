"""Tests for Portuguese date normalization."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.services.date_parser import (
    LISBON_TZ,
    ensure_iso_datetime,
    parse_pt_datetime,
)


def test_none_returns_none() -> None:
    assert parse_pt_datetime(None) is None
    assert parse_pt_datetime("") is None


def test_invalid_returns_none() -> None:
    assert parse_pt_datetime("blablabla xpto") is None


def test_iso_with_offset_is_preserved() -> None:
    result = parse_pt_datetime("2026-04-23T15:00:00+01:00")
    assert result is not None
    assert result.year == 2026
    assert result.month == 4
    assert result.day == 23
    assert result.hour == 15
    assert result.tzinfo is not None


def test_iso_naive_gets_lisbon_tz() -> None:
    result = parse_pt_datetime("2026-04-23T15:00:00")
    assert result is not None
    assert result.tzinfo is not None


def test_iso_z_suffix() -> None:
    result = parse_pt_datetime("2026-04-23T15:00:00Z")
    assert result is not None
    assert result.hour == 15


def test_amanha_returns_tomorrow() -> None:
    result = parse_pt_datetime("amanhã")
    assert result is not None
    tomorrow = datetime.now(LISBON_TZ) + timedelta(days=1)
    assert result.date() == tomorrow.date()


def test_proxima_quinta_returns_future_thursday() -> None:
    result = parse_pt_datetime("próxima quinta")
    assert result is not None
    assert result.weekday() == 3  # Thursday
    assert result > datetime.now(LISBON_TZ)


def test_daqui_a_duas_semanas() -> None:
    result = parse_pt_datetime("daqui a 2 semanas")
    assert result is not None
    expected = datetime.now(LISBON_TZ) + timedelta(days=14)
    # Allow ±1 day tolerance (dateparser may pick start/end of day)
    delta = abs((result - expected).total_seconds())
    assert delta < 2 * 86400  # within 2 days


def test_hoje_as_15h() -> None:
    result = parse_pt_datetime("hoje às 15h")
    assert result is not None
    assert result.hour == 15
    assert result.date() == datetime.now(LISBON_TZ).date()


def test_ensure_iso_valid_returns_iso_string() -> None:
    result = ensure_iso_datetime("amanhã às 10h")
    assert result is not None
    # Should be parseable back
    parsed = datetime.fromisoformat(result)
    assert parsed.hour == 10


def test_ensure_iso_unparseable_with_fallback() -> None:
    result = ensure_iso_datetime("zxxy", fallback_hours_from_now=1)
    assert result is not None
    parsed = datetime.fromisoformat(result)
    assert (parsed - datetime.now(LISBON_TZ)).total_seconds() > 0


def test_ensure_iso_unparseable_without_fallback() -> None:
    assert ensure_iso_datetime("zxxy") is None
