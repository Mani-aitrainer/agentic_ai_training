from __future__ import annotations

import pytest

from dispute_agent.fraud import (
    FraudService,
    FraudServiceUnavailable,
    score_fraud,
)



LOW_MERCHANT = {"risk_rating": "low", "chargeback_rate": 0.2, "country": "IN"}
HIGH_MERCHANT = {"risk_rating": "high", "chargeback_rate": 4.8, "country": "RU"}
SAFE_CUSTOMER = {"home_country": "IN", "account_age_months": 84, "prior_fraud_confirmed": 0}


def _txn(**over):
    base = {
        "amount": 1000.0,
        "timestamp": "2026-07-10T14:00:00",
        "card_present": True,
        "country": "IN",
    }
    base.update(over)
    return base


def test_clean_domestic_card_present_is_low_risk():
    res = score_fraud(_txn(), SAFE_CUSTOMER, LOW_MERCHANT)
    assert res.score == 0.0
    assert res.signals == []


def test_high_risk_merchant_adds_signal():
    res = score_fraud(_txn(), SAFE_CUSTOMER, HIGH_MERCHANT)
    assert "high_risk_merchant" in res.signals
    assert res.score > 0


def test_cross_border_detected():
    res = score_fraud(_txn(country="RU"), SAFE_CUSTOMER, LOW_MERCHANT)
    assert "cross_border_txn" in res.signals


def test_odd_hours_detected():
    res = score_fraud(_txn(timestamp="2026-07-10T02:30:00"), SAFE_CUSTOMER, LOW_MERCHANT)
    assert "odd_hours" in res.signals


def test_score_is_capped_at_one():
    res = score_fraud(
        _txn(amount=90000, country="RU", card_present=False, timestamp="2026-07-10T02:00:00"),
        {"home_country": "IN", "account_age_months": 2, "prior_fraud_confirmed": 3},
        HIGH_MERCHANT,
    )
    assert res.score == 1.0


def test_malformed_timestamp_is_tolerated():
    res = score_fraud(_txn(timestamp="garbage"), SAFE_CUSTOMER, LOW_MERCHANT)
    assert "odd_hours" not in res.signals  # no crash, just no signal


# --- the flaky service wrapper ---
def test_service_fails_then_succeeds():
    svc = FraudService(fail_times=2)
    with pytest.raises(FraudServiceUnavailable):
        svc.score(_txn(), SAFE_CUSTOMER, LOW_MERCHANT)
    with pytest.raises(FraudServiceUnavailable):
        svc.score(_txn(), SAFE_CUSTOMER, LOW_MERCHANT)
    # third call succeeds
    res = svc.score(_txn(), SAFE_CUSTOMER, LOW_MERCHANT)
    assert res.score == 0.0
    assert svc.calls == 3
