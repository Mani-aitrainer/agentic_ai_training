"""Triage, Policy, and Resolution agents, plus the Supervisor.

All are built by small factories that close over injected dependencies, keeping
the same testability seam as the original project.
"""
from __future__ import annotations

from typing import Any, Callable

from ..classifier import Classifier
from ..config import settings
from ..prompts import RESOLUTION_SYSTEM, resolution_user_prompt
from ..scratchpad import note
from ..state import DisputeState


# --------------------------------------------------------------------------
# Triage Agent -- wraps the injected classifier (OpenAI or stub) as an agent.
# --------------------------------------------------------------------------
def make_triage_agent(classifier: Classifier):
    def triage_agent(state: DisputeState) -> dict[str, Any]:
        attempts = state.get("triage_attempts", 0) + 1
        result = classifier.classify(
            customer_statement=state["dispute"]["customer_statement"],
            transaction=state["transaction"],
        )
        return {
            "category": result.category,
            "category_confidence": result.confidence,
            "triage_attempts": attempts,
            "agent_messages": [
                note("triage", f"category={result.category} conf={result.confidence:.2f}")
            ],
            "audit_trail": [
                f"triage_agent: {result.category} (conf={result.confidence:.2f}, attempt {attempts})"
            ],
        }

    return triage_agent



# --------------------------------------------------------------------------
# Policy Agent -- deterministic decision engine (the old `decide`, as an agent).
# --------------------------------------------------------------------------
def make_policy_agent():
    def policy_agent(state: DisputeState) -> dict[str, Any]:
        category = state.get("category", "OTHER")
        amount = float(state["transaction"]["amount"])
        fraud_score = state.get("fraud_score", 0.0)

        if category == "DUPLICATE" and state["transaction"].get("duplicate_of"):
            if amount < settings.duplicate_auto_resolve_max:
                out = _resolve(amount, "Confirmed duplicate charge below auto-resolve limit.")
            else:
                out = _escalate("Confirmed duplicate but amount exceeds auto-resolve limit.")
        elif category in ("FRAUD", "UNRECOGNIZED") and fraud_score >= settings.fraud_score_threshold:
            out = _resolve(amount, f"Fraud signals strong (score={fraud_score}); provisional refund.")
        elif category in ("FRAUD", "UNRECOGNIZED"):
            out = _escalate(f"Fraud alleged but signals weak (score={fraud_score}); analyst review.")
        elif category == "SERVICE_NOT_RENDERED":
            out = _escalate("Service-not-rendered claim requires merchant evidence review.")
        else:
            out = _escalate("Unclassified dispute; routed to analyst.")

        out["agent_messages"] = [note("policy", f"{out['decision']} - {out['reason']}")]
        return out

    return policy_agent

def _resolve(amount: float, reason: str) -> dict[str, Any]:
    needs_human = amount >= settings.human_approval_threshold
    return {
        "decision": "AUTO_RESOLVE",
        "refund_amount": amount,
        "requires_human_approval": needs_human,
        "reason": reason,
        "audit_trail": [f"policy_agent: AUTO_RESOLVE (human_approval={needs_human}) - {reason}"],
    }


def _escalate(reason: str) -> dict[str, Any]:
    return {
        "decision": "ESCALATE",
        "requires_human_approval": False,
        "reason": reason,
        "audit_trail": [f"policy_agent: ESCALATE - {reason}"],
    }




# --------------------------------------------------------------------------
# Resolution Agent -- drafts the customer-facing message.
# --------------------------------------------------------------------------
class MessageWriter:
    """Protocol-ish: anything with .write(state) -> str."""

    def write(self, state: DisputeState) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class StubMessageWriter:
    """Deterministic customer message for offline runs."""

    def write(self, state: DisputeState) -> str:
        name = state.get("customer", {}).get("name", "Customer")
        outcome = state.get("outcome")
        if outcome == "REFUNDED":
            return (f"Dear {name}, we have reviewed your dispute and processed a refund of "
                    f"Rs.{state.get('refund_amount')}. It should reflect in 3-5 working days. "
                    f"We're sorry for the inconvenience.")
        if outcome == "REJECTED":
            return (f"Dear {name}, after reviewing your dispute we are unable to process a refund "
                    f"as the transaction appears valid. Please contact us if you have more details.")
        return (f"Dear {name}, your dispute has been escalated to a specialist analyst who will "
                f"review it and get back to you shortly. Thank you for your patience.")


class OpenAIMessageWriter:
    """Live customer message via OpenAI."""

    def __init__(self, model: str, temperature: float = 0.3) -> None:
        from langchain_openai import ChatOpenAI

        self._llm = ChatOpenAI(model=model, temperature=temperature)

    def write(self, state: DisputeState) -> str:
        messages = [
            {"role": "system", "content": RESOLUTION_SYSTEM},
            {"role": "user", "content": resolution_user_prompt(state)},
        ]
        return self._llm.invoke(messages).text


def make_resolution_agent(writer: MessageWriter):
    def resolution_agent(state: DisputeState) -> dict[str, Any]:
        message = writer.write(state)
        return {
            "customer_message": message,
            "agent_messages": [note("resolution", "drafted customer message")],
            "audit_trail": ["resolution_agent: customer message drafted"],
        }

    return resolution_agent




# --------------------------------------------------------------------------
# Supervisor -- dynamic task allocation. Reads state, picks the next agent.
# --------------------------------------------------------------------------
def make_supervisor():
    """The orchestrator. Decides which specialist runs next based on state.

    This is dynamic task allocation: the path is not hardcoded. A clean
    duplicate skips fraud investigation; a fraud/unrecognized case always gets
    investigated; low-confidence triage loops back for another pass.
    """

    def supervisor(state: DisputeState) -> dict[str, Any]:
        category = state.get("category")
        confidence = state.get("category_confidence", 0.0)
        attempts = state.get("triage_attempts", 0)

        # 1. No triage yet -> triage first.
        if category is None:
            nxt = "triage_agent"
            why = "no classification yet"
        # 2. Low-confidence triage -> loop back, but bounded.
        elif confidence < settings.triage_confidence_threshold and attempts < settings.max_triage_attempts:
            nxt = "triage_agent"
            why = f"low confidence {confidence:.2f}, re-triage (attempt {attempts})"
        # 3. Fraud/unrecognized and not yet investigated -> investigate.
        elif category in ("FRAUD", "UNRECOGNIZED") and "fraud_score" not in state:
            nxt = "fraud_investigator"
            why = f"{category} needs fraud investigation"
        # 4. Everything gathered -> hand to policy for the decision.
        else:
            nxt = "policy_agent"
            why = "context gathered, ready for policy decision"

        return {
            "next_agent": nxt,
            "agent_messages": [note("supervisor", f"-> {nxt} ({why})")],
            "audit_trail": [f"supervisor: dispatch -> {nxt} ({why})"],
        }

    return supervisor