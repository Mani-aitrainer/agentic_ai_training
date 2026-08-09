"""Shared pytest fixtures.

Adds src/ to the path and provides ready-made stub dependencies so every test
runs fully offline (no OpenAI, no filesystem surprises).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from dispute_agent.agents.specialists import StubMessageWriter  # noqa: E402
from dispute_agent.classifier import StubClassifier  # noqa: E402
from dispute_agent.data_access import InMemoryRepository  # noqa: E402
from dispute_agent.dependencies import Dependencies  # noqa: E402
from dispute_agent.fraud import FraudService  # noqa: E402


@pytest.fixture
def sample_tables():
    """A minimal but complete set of records covering the main branches."""
    return {
        "disputes": {
            "D_DUP": {"dispute_id": "D_DUP", "txn_id": "T_DUP",
                      "customer_statement": "I was charged twice, this is a duplicate."},
            "D_FRAUD": {"dispute_id": "D_FRAUD", "txn_id": "T_FRAUD",
                        "customer_statement": "I never made this, someone stole my card."},
            "D_SNR": {"dispute_id": "D_SNR", "txn_id": "T_OK",
                      "customer_statement": "The delivery never arrived."},
        },
        "transactions": {
            "T_DUP": {"txn_id": "T_DUP", "customer_id": "C1", "merchant_id": "M_LOW",
                      "amount": 8000.0, "timestamp": "2026-07-10T14:00:00",
                      "card_present": False, "country": "IN", "duplicate_of": "T_ORIG"},
            "T_FRAUD": {"txn_id": "T_FRAUD", "customer_id": "C_NEW", "merchant_id": "M_HIGH",
                        "amount": 65000.0, "timestamp": "2026-07-20T02:00:00",
                        "card_present": False, "country": "RU", "duplicate_of": None},
            "T_OK": {"txn_id": "T_OK", "customer_id": "C1", "merchant_id": "M_LOW",
                     "amount": 1500.0, "timestamp": "2026-07-18T09:00:00",
                     "card_present": False, "country": "IN", "duplicate_of": None},
        },
        "customers": {
            "C1": {"customer_id": "C1", "home_country": "IN", "account_age_months": 84,
                   "prior_fraud_confirmed": 0},
            "C_NEW": {"customer_id": "C_NEW", "home_country": "IN", "account_age_months": 3,
                      "prior_fraud_confirmed": 0},
        },
        "merchants": {
            "M_LOW": {"merchant_id": "M_LOW", "risk_rating": "low", "chargeback_rate": 0.2,
                      "country": "IN"},
            "M_HIGH": {"merchant_id": "M_HIGH", "risk_rating": "high", "chargeback_rate": 4.8,
                       "country": "RU"},
        },
    }


@pytest.fixture
def repo(sample_tables):
    return InMemoryRepository(**sample_tables)


@pytest.fixture
def deps(repo):
    return Dependencies(
        repo=repo,
        classifier=StubClassifier(),
        fraud_service=FraudService(),
        message_writer=StubMessageWriter(),
    )
