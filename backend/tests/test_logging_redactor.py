"""
Testes unitários para o processor de redacção PII do structlog.

Task 9 (REFACTOR) · Sprint 1 · E1 · LOGGING-POLICY.md §4.

Cobre o processor isoladamente (sem full pipeline): entra um `event_dict`
heterogéneo e sai o mesmo dict com valores sensíveis redactados. Estes
testes são a primeira linha de defesa contra AC-8 (tokens nunca em logs)
e contra fuga de emails/credenciais para Axiom/Sentry.

Filosofia:
    - Keys sensíveis (regex `(token|secret|key|authorization|password|
      refresh|access|code)`, case-insensitive) → value = "***"
    - Values contendo padrão email → "***@***"
    - Recursão em dicts aninhados
    - Keys benignas (status_code, user_id, latency_ms) passam intactas
"""
from __future__ import annotations

from app.logging import _redact_pii


# ---------------------------------------------------------------------------
# Key-based redaction
# ---------------------------------------------------------------------------


def test_redacts_token_key() -> None:
    """`access_token`, `id_token`, `token` → valor substituído por ***."""
    out = _redact_pii(None, "info", {"access_token": "ya29.abc123"})
    assert out["access_token"] == "***"


def test_redacts_refresh_token_key() -> None:
    """`refresh_token` é a credencial mais sensível — tem de ser redactada."""
    out = _redact_pii(None, "info", {"refresh_token": "1//0abcdef"})
    assert out["refresh_token"] == "***"


def test_redacts_authorization_header_key() -> None:
    """`Authorization` header (case-insensitive) com Bearer token → ***."""
    out = _redact_pii(
        None,
        "info",
        {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9..."},
    )
    assert out["Authorization"] == "***"


# ---------------------------------------------------------------------------
# Value-based redaction (email regex)
# ---------------------------------------------------------------------------


def test_redacts_email_values() -> None:
    """Qualquer value string contendo email é redactado para `***@***`.

    Cobre o caso de um developer esquecer-se e passar `user@gmail.com`
    num campo tipo `message` ou `detail`.
    """
    out = _redact_pii(None, "info", {"message": "login for user@gmail.com ok"})
    assert "user@gmail.com" not in out["message"]
    assert "***@***" in out["message"]


# ---------------------------------------------------------------------------
# Recursion
# ---------------------------------------------------------------------------


def test_redacts_nested_dict() -> None:
    """Redacção recursiva em dicts aninhados — caso típico `extra={...}`."""
    event = {
        "event": "token_exchange",
        "context": {
            "access_token": "ya29.secret",
            "status_code": 200,
            "inner": {"refresh_token": "1//leaked"},
        },
    }
    out = _redact_pii(None, "info", event)
    assert out["context"]["access_token"] == "***"
    assert out["context"]["status_code"] == 200  # benigno passa
    assert out["context"]["inner"]["refresh_token"] == "***"


# ---------------------------------------------------------------------------
# Non-sensitive keys preserved
# ---------------------------------------------------------------------------


def test_preserves_non_sensitive_keys() -> None:
    """Keys neutras (status_code, user_id UUID, latency_ms, event) intactas."""
    event_dict = {
        "event": "email_sent",
        "status_code": 200,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "latency_ms": 234,
        "gmail_message_id": "18abcd1234",
    }
    out = _redact_pii(None, "info", event_dict)
    assert out["event"] == "email_sent"
    assert out["status_code"] == 200
    assert out["user_id"] == "00000000-0000-0000-0000-000000000001"
    assert out["latency_ms"] == 234
    assert out["gmail_message_id"] == "18abcd1234"
