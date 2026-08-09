"""Unit tests for the Supervisor -- dynamic task allocation.

The supervisor NODE decides which agent runs next (writes next_agent);
the ROUTER just reads it. Both are tested here in isolation.
"""
from __future__ import annotations

from dispute_agent.agents.specialists import make_supervisor
from dispute_agent.config import settings
from dispute_agent.routers import supervisor_route

supervisor = make_supervisor()


def test_no_classification_goes_to_triage():
    out = supervisor({})
    assert out["next_agent"] == "triage_agent"


def test_low_confidence_loops_back_to_triage():
    out = supervisor({"category": "OTHER", "category_confidence": 0.2, "triage_attempts": 1})
    assert out["next_agent"] == "triage_agent"


def test_low_confidence_but_attempts_exhausted_moves_on():
    out = supervisor(
        {"category": "OTHER", "category_confidence": 0.2,
         "triage_attempts": settings.max_triage_attempts}
    )
    assert out["next_agent"] == "policy_agent"


def test_fraud_category_routes_to_investigator():
    out = supervisor({"category": "FRAUD", "category_confidence": 0.9, "triage_attempts": 1})
    assert out["next_agent"] == "fraud_investigator"


def test_fraud_already_investigated_goes_to_policy():
    out = supervisor(
        {"category": "FRAUD", "category_confidence": 0.9, "triage_attempts": 1,
         "fraud_score": 0.8}
    )
    assert out["next_agent"] == "policy_agent"


def test_duplicate_skips_investigation_goes_to_policy():
    # dynamic allocation: a confident non-fraud category never touches the investigator
    out = supervisor({"category": "DUPLICATE", "category_confidence": 0.95, "triage_attempts": 1})
    assert out["next_agent"] == "policy_agent"


def test_supervisor_route_reads_next_agent():
    assert supervisor_route({"next_agent": "fraud_investigator"}) == "fraud_investigator"
