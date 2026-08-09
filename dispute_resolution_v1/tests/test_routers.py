"""Unit tests for the conditional-edge routers.

These are pure state->string functions, so testing is: build a dict, assert the
next node name. This is the Section 4 point about testing transitions in
isolation from the graph.
"""
from __future__ import annotations

from dispute_agent.config import settings
from dispute_agent.routers import after_decide, after_fraud_check


# --- after_fraud_check: the retry loop transition ---
def test_service_available_moves_to_decide():
    assert after_fraud_check({"service_available": True}) == "decide"


def test_service_down_with_retries_left_loops_back():
    state = {"service_available": False, "fraud_check_attempts": 1}
    assert after_fraud_check(state) == "fraud_check"


def test_service_down_at_limit_escalates():
    state = {"service_available": False,
             "fraud_check_attempts": settings.max_fraud_check_attempts}
    assert after_fraud_check(state) == "escalate"


# --- after_decide: the three-way branch ---
def test_resolve_without_human_goes_to_refund():
    state = {"decision": "AUTO_RESOLVE", "requires_human_approval": False}
    assert after_decide(state) == "refund"


def test_resolve_with_human_goes_to_approval():
    state = {"decision": "AUTO_RESOLVE", "requires_human_approval": True}
    assert after_decide(state) == "human_approval"


def test_reject_decision_routes_to_reject():
    assert after_decide({"decision": "AUTO_REJECT"}) == "reject"


def test_escalate_decision_routes_to_escalate():
    assert after_decide({"decision": "ESCALATE"}) == "escalate"
