"""Unit tests for individual node handlers.

Nodes are tested in isolation by building them with stub dependencies via
make_nodes(deps) and calling them with a hand-made state dict. No graph needed.
"""
from __future__ import annotations

from dispute_agent.config import settings
from dispute_agent.fraud import FraudService
from dispute_agent.nodes import make_nodes


def test_intake_loads_all_context(deps):
    nodes = make_nodes(deps)
    out = nodes["intake"]({"dispute_id": "D_DUP"})
    assert out["transaction"]["txn_id"] == "T_DUP"
    assert out["customer"]["customer_id"] == "C1"
    assert out["merchant"]["merchant_id"] == "M_LOW"
    assert out["fraud_check_attempts"] == 0
    assert out["audit_trail"]  # non-empty


def test_classify_uses_injected_classifier(deps):
    nodes = make_nodes(deps)
    state = {"dispute": {"customer_statement": "I never made this, someone stole my card."},
             "transaction": {}}
    out = nodes["classify"](state)
    assert out["category"] == "FRAUD"
    assert 0.0 <= out["category_confidence"] <= 1.0


def test_fraud_check_success_populates_score(deps):
    nodes = make_nodes(deps)
    state = {
        "fraud_check_attempts": 0,
        "transaction": {"amount": 1000, "timestamp": "2026-07-10T14:00:00",
                        "card_present": True, "country": "IN"},
        "customer": {"home_country": "IN", "account_age_months": 84, "prior_fraud_confirmed": 0},
        "merchant": {"risk_rating": "low", "chargeback_rate": 0.1, "country": "IN"},
    }
    out = nodes["fraud_check"](state)
    assert out["service_available"] is True
    assert out["fraud_check_attempts"] == 1
    assert "fraud_score" in out


def test_fraud_check_outage_sets_unavailable(repo):
    from dispute_agent.agents.specialists import StubMessageWriter
    from dispute_agent.classifier import StubClassifier
    from dispute_agent.dependencies import Dependencies

    deps = Dependencies(repo=repo, classifier=StubClassifier(),
                        fraud_service=FraudService(fail_times=1),
                        message_writer=StubMessageWriter())
    nodes = make_nodes(deps)
    state = {"fraud_check_attempts": 0, "transaction": {}, "customer": {}, "merchant": {}}
    out = nodes["fraud_check"](state)
    assert out["service_available"] is False
    assert out["fraud_check_attempts"] == 1


def test_decide_duplicate_small_amount_auto_resolves(deps):
    nodes = make_nodes(deps)
    state = {
        "category": "DUPLICATE",
        "transaction": {"amount": 8000.0, "duplicate_of": "T_ORIG"},
        "fraud_score": 0.1,
    }
    out = nodes["decide"](state)
    assert out["decision"] == "AUTO_RESOLVE"
    assert out["requires_human_approval"] is False  # 8000 < threshold


def test_decide_large_refund_requires_human(deps):
    nodes = make_nodes(deps)
    state = {
        "category": "FRAUD",
        "transaction": {"amount": settings.human_approval_threshold + 1, "duplicate_of": None},
        "fraud_score": 0.9,
    }
    out = nodes["decide"](state)
    assert out["decision"] == "AUTO_RESOLVE"
    assert out["requires_human_approval"] is True


def test_decide_weak_fraud_signal_escalates(deps):
    nodes = make_nodes(deps)
    state = {
        "category": "FRAUD",
        "transaction": {"amount": 5000.0, "duplicate_of": None},
        "fraud_score": 0.1,  # below threshold
    }
    out = nodes["decide"](state)
    assert out["decision"] == "ESCALATE"


def test_refund_respects_officer_rejection(deps):
    nodes = make_nodes(deps)
    state = {
        "dispute_id": "D1",
        "requires_human_approval": True,
        "approval_decision": "reject",
        "refund_amount": 65000.0,
    }
    out = nodes["refund"](state)
    assert out["outcome"] == "REJECTED"
