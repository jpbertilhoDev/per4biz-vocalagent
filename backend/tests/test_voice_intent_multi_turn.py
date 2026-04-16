"""Multi-turn intent resolution — AC-E9.2.

Runs 20 cases against the real Groq API. Requires GROQ_API_KEY env.
Skipped unless RUN_NETWORK_TESTS=1 because each case costs a real API call.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.services.voice_intent import classify_intent

FIXTURES = Path(__file__).parent / "fixtures" / "multi_turn_cases.json"

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_NETWORK_TESTS"),
    reason="Set RUN_NETWORK_TESTS=1 to run Groq-backed multi-turn tests",
)


def _load_cases() -> list[dict]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_multi_turn_intent(case: dict) -> None:
    """Classify each case; assert intent matches expected (per-case view)."""
    result = classify_intent(case["transcript"], history=case["history"])

    expected_intent = case["expected"]["intent"]
    assert result["intent"] == expected_intent, (
        f"{case['id']}: expected {expected_intent}, got {result['intent']}. "
        f"Transcript: {case['transcript']!r}"
    )

    # Optional: params subset match
    expected_params = case["expected"].get("paramsContain")
    if expected_params:
        for key, value in expected_params.items():
            assert key in result["params"], f"{case['id']}: param {key} missing"
            assert value in str(result["params"][key]), (
                f"{case['id']}: param {key}={result['params'][key]} does not contain {value}"
            )


def test_accuracy_threshold() -> None:
    """Aggregate: ≥ 18/20 (90%) casos devem passar — AC-E9.2."""
    cases = _load_cases()
    passes = 0
    failures: list[str] = []

    for case in cases:
        try:
            result = classify_intent(case["transcript"], history=case["history"])
            if result["intent"] == case["expected"]["intent"]:
                passes += 1
            else:
                failures.append(
                    f"{case['id']}: expected {case['expected']['intent']}, "
                    f"got {result['intent']}"
                )
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{case['id']}: exception {exc}")

    accuracy = passes / len(cases)
    print(f"\nMulti-turn accuracy: {passes}/{len(cases)} = {accuracy:.0%}")
    for f in failures:
        print(f"  FAIL {f}")

    assert accuracy >= 0.9, (
        f"Accuracy {accuracy:.0%} below AC-E9.2 threshold of 90%. "
        f"Failures: {failures}"
    )
