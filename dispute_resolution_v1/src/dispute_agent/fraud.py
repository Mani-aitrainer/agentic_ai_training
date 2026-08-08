"""Fraud scoring.

Two things live here:
  * score_fraud() -- a pure, deterministic function of the case facts. Pure
    functions are the easiest thing in the world to unit test, so the risk
    logic lives here rather than inside a node.
  * FraudService -- a thin wrapper that *may* be unavailable, to simulate a
    real external scoring API. The graph handles the outage with a retry loop.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FraudResult:
    score: float           # 0-1, higher = more likely fraud
    signals: list[str]


def score_fraud(transaction: dict, customer: dict, merchant: dict) -> FraudResult:
    """Deterministic fraud score from case facts. Pure function -> trivial to test."""
    score = 0.0
    signals: list[str] = []

    # High-risk merchant category / rating
    if merchant.get("risk_rating") == "high":
        score += 0.35
        signals.append("high_risk_merchant")
    if merchant.get("chargeback_rate", 0) > 2.0:
        score += 0.15
        signals.append("elevated_merchant_chargeback_rate")

    # Cross-border relative to the customer's home country
    if transaction.get("country") and transaction["country"] != customer.get("home_country"):
        score += 0.25
        signals.append("cross_border_txn")

    # Card-not-present online
    if not transaction.get("card_present", False):
        score += 0.1
        signals.append("card_not_present")

    # Odd-hours transaction (00:00-05:00 local)
    ts = transaction.get("timestamp", "")
    hour = _hour_of(ts)
    if hour is not None and 0 <= hour < 5:
        score += 0.15
        signals.append("odd_hours")

    # Customer history
    if customer.get("prior_fraud_confirmed", 0) > 0:
        score += 0.1
        signals.append("prior_confirmed_fraud")
    if customer.get("account_age_months", 999) < 12:
        score += 0.1
        signals.append("new_account")

    # High ticket size
    if transaction.get("amount", 0) >= 50000:
        score += 0.1
        signals.append("high_value")

    return FraudResult(score=round(min(score, 1.0), 2), signals=signals)


def _hour_of(timestamp: str) -> int | None:
    """Extract the hour from an ISO 8601 timestamp, tolerantly."""
    try:
        return int(timestamp.split("T")[1][:2])
    except (IndexError, ValueError):
        return None


class FraudServiceUnavailable(RuntimeError):
    """Raised when the (simulated) external scoring service is down."""


class FraudService:
    """Wraps score_fraud() but can be told to fail the first N calls, so we can
    demonstrate the graph's retry loop without a real flaky network."""

    def __init__(self, fail_times: int = 0) -> None:
        self._remaining_failures = fail_times
        self.calls = 0

    def score(self, transaction: dict, customer: dict, merchant: dict) -> FraudResult:
        self.calls += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise FraudServiceUnavailable("fraud scoring service timed out")
        return score_fraud(transaction, customer, merchant)
