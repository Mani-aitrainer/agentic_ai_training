"""Node handlers for the dispute resolution state machine.

Each node has the LangGraph signature ``(state) -> partial_state_dict``.
They are produced by ``make_nodes(deps)`` so they can close over injected
dependencies (repo / classifier / fraud service) while still presenting the
plain single-argument signature LangGraph expects.
"""
from __future__ import annotations

from typing import Any, Callable

from langgraph.types import interrupt

from .config import settings
from .data_access import RecordNotFound
from .dependencies import Dependencies
from .fraud import FraudServiceUnavailable
from .state import DisputeState

NodeFn = Callable[[DisputeState], dict[str, Any]]


def make_nodes(deps: Dependencies) -> dict[str, NodeFn]:
    """Return the named node handlers, each bound to the given dependencies."""

    # -- intake: load all the context for this dispute ------------------
    def intake(state: DisputeState) -> dict[str, Any]:
        dispute = deps.repo.get_dispute(state["dispute_id"])
        txn = deps.repo.get_transaction(dispute["txn_id"])
        customer = deps.repo.get_customer(txn["customer_id"])
        merchant = deps.repo.get_merchant(txn["merchant_id"])
        return {
            "dispute": dispute,
            "transaction": txn,
            "customer": customer,
            "merchant": merchant,
            "fraud_check_attempts": 0,
            "audit_trail": [f"intake: loaded dispute {state['dispute_id']} for txn {txn['txn_id']}"],
        }

    # -- classify: the LLM boundary -------------------------------------
    def classify(state: DisputeState) -> dict[str, Any]:
        result = deps.classifier.classify(
            customer_statement=state["dispute"]["customer_statement"],
            transaction=state["transaction"],
        )
        return {
            "category": result.category,
            "category_confidence": result.confidence,
            "audit_trail": [
                f"classify: {result.category} (conf={result.confidence:.2f})"
            ],
        }

    # -- fraud_check: calls a flaky service; may need retrying ----------
    def fraud_check(state: DisputeState) -> dict[str, Any]:
        attempts = state.get("fraud_check_attempts", 0) + 1
        try:
            res = deps.fraud_service.score(
                state["transaction"], state["customer"], state["merchant"]
            )
        except FraudServiceUnavailable:
            return {
                "fraud_check_attempts": attempts,
                "service_available": False,
                "audit_trail": [f"fraud_check: service unavailable (attempt {attempts})"],
            }
        return {
            "fraud_check_attempts": attempts,
            "service_available": True,
            "fraud_score": res.score,
            "fraud_signals": res.signals,
            "audit_trail": [
                f"fraud_check: score={res.score} signals={res.signals} (attempt {attempts})"
            ],
        }

    # -- decide: deterministic policy engine ----------------------------
    def decide(state: DisputeState) -> dict[str, Any]:
        category = state["category"]
        amount = float(state["transaction"]["amount"])
        fraud_score = state.get("fraud_score", 0.0)

        # 1. Clear duplicate, modest amount -> refund automatically.
        if category == "DUPLICATE" and state["transaction"].get("duplicate_of"):
            if amount < settings.duplicate_auto_resolve_max:
                return _resolve(amount, "Confirmed duplicate charge below auto-resolve limit.")
            return _escalate("Confirmed duplicate but amount exceeds auto-resolve limit.")

        # 2. Fraud allegation with strong fraud signals -> refund (chargeback path).
        if category in ("FRAUD", "UNRECOGNIZED") and fraud_score >= settings.fraud_score_threshold:
            return _resolve(amount, f"Fraud signals strong (score={fraud_score}); provisional refund.")

        # 3. Fraud allegation but weak signals -> needs a human, don't auto-reject.
        if category in ("FRAUD", "UNRECOGNIZED"):
            return _escalate(f"Fraud alleged but signals weak (score={fraud_score}); analyst review.")

        # 4. Service not rendered -> merchant evidence needed, human decides.
        if category == "SERVICE_NOT_RENDERED":
            return _escalate("Service-not-rendered claim requires merchant evidence review.")

        # 5. Everything else.
        return _escalate("Unclassified dispute; routed to analyst.")

    # -- human approval gate (interrupt) --------------------------------
    def human_approval(state: DisputeState) -> dict[str, Any]:
        decision = interrupt(
            {
                "question": "Approve this refund?",
                "dispute_id": state["dispute_id"],
                "amount": state["refund_amount"],
                "reason": state["reason"],
            }
        )
        approved = str(decision).lower() in ("yes", "approve", "approved", "true")
        return {
            "approval_decision": "approve" if approved else "reject",
            "audit_trail": [f"human_approval: officer said {decision!r}"],
        }

    # -- terminal nodes -------------------------------------------------
    def refund(state: DisputeState) -> dict[str, Any]:
        # If a human gate ran and rejected, honour that.
        if state.get("requires_human_approval") and state.get("approval_decision") == "reject":
            return {
                "outcome": "REJECTED",
                "audit_trail": [f"refund: blocked by officer for {state['dispute_id']}"],
            }
        return {
            "outcome": "REFUNDED",
            "audit_trail": [
                f"refund: Rs.{state['refund_amount']} credited for {state['dispute_id']}"
            ],
        }

    def reject(state: DisputeState) -> dict[str, Any]:
        return {
            "outcome": "REJECTED",
            "audit_trail": [f"reject: dispute {state['dispute_id']} rejected"],
        }

    def escalate(state: DisputeState) -> dict[str, Any]:
        return {
            "outcome": "ESCALATED",
            "audit_trail": [
                f"escalate: dispute {state['dispute_id']} sent to human analyst queue"
            ],
        }

    return {
        "intake": intake,
        "classify": classify,
        "fraud_check": fraud_check,
        "decide": decide,
        "human_approval": human_approval,
        "refund": refund,
        "reject": reject,
        "escalate": escalate,
    }


# --- small helpers used by decide() to build consistent partial states ---
def _resolve(amount: float, reason: str) -> dict[str, Any]:
    needs_human = amount >= settings.human_approval_threshold
    return {
        "decision": "AUTO_RESOLVE",
        "refund_amount": amount,
        "requires_human_approval": needs_human,
        "reason": reason,
        "audit_trail": [f"decide: AUTO_RESOLVE (human_approval={needs_human}) - {reason}"],
    }


def _escalate(reason: str) -> dict[str, Any]:
    return {
        "decision": "ESCALATE",
        "requires_human_approval": False,
        "reason": reason,
        "audit_trail": [f"decide: ESCALATE - {reason}"],
    }


def _reject(reason: str) -> dict[str, Any]:
    return {
        "decision": "AUTO_REJECT",
        "requires_human_approval": False,
        "reason": reason,
        "audit_trail": [f"decide: AUTO_REJECT - {reason}"],
    }
