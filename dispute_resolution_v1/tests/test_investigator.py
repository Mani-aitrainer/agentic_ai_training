"""Tests for the tool-calling Fraud Investigator agent and its LangChain tools.

Covers: the @tool functions read from the bound repository, and the full
agent<->tools loop runs offline via the scripted model and writes fraud_score
back into shared state.
"""
from __future__ import annotations

from dispute_agent.agents.fraud_investigator import make_fraud_investigator
from dispute_agent.tools import (
    bind_repository,
    compute_fraud_signals,
    lookup_customer_history,
    lookup_merchant,
    lookup_transaction,
)


# --- the LangChain tools ---
def test_tools_read_from_bound_repository(repo):
    bind_repository(repo)
    txn = lookup_transaction.invoke({"txn_id": "T_FRAUD"})
    assert txn["amount"] == 65000.0
    merchant = lookup_merchant.invoke({"merchant_id": "M_HIGH"})
    assert merchant["risk_rating"] == "high"
    hist = lookup_customer_history.invoke({"customer_id": "C_NEW"})
    assert hist["account_age_months"] == 3


def test_compute_fraud_signals_tool(repo):
    bind_repository(repo)
    result = compute_fraud_signals.invoke({"txn_id": "T_FRAUD"})
    assert result["fraud_score"] >= 0.6            # high-risk case
    assert "high_risk_merchant" in result["signals"]


def test_missing_id_returns_error_not_exception(repo):
    bind_repository(repo)
    assert "error" in lookup_transaction.invoke({"txn_id": "NOPE"})


# --- the full tool-loop agent (offline) ---
def test_investigator_runs_tool_loop_and_writes_state(repo):
    bind_repository(repo)
    investigator = make_fraud_investigator()  # scripted offline model
    state = {
        "transaction": {"txn_id": "T_FRAUD", "customer_id": "C_NEW", "merchant_id": "M_HIGH"},
        "category": "FRAUD",
    }
    out = investigator(state)
    assert out["fraud_score"] >= 0.6
    assert out["fraud_signals"]                     # non-empty
    assert "STRONG" in out["agent_messages"][0]["message"]
    assert "fraud_investigator" in out["audit_trail"][0]


def test_investigator_low_risk_is_weak(repo):
    bind_repository(repo)
    investigator = make_fraud_investigator()
    state = {
        "transaction": {"txn_id": "T_OK", "customer_id": "C1", "merchant_id": "M_LOW"},
        "category": "UNRECOGNIZED",
    }
    out = investigator(state)
    assert out["fraud_score"] < 0.6
    assert "WEAK" in out["agent_messages"][0]["message"]
