"""The shared state for the multi-agent dispute resolution graph.

Agents never call each other directly. They coordinate ONLY by reading and
writing this shared state -- that is the core multi-agent-via-graph-state idea.

State ownership contract (who writes what):
    intake              -> dispute, transaction, customer, merchant
    supervisor          -> next_agent, triage_attempts (routing control)
    triage_agent        -> category, category_confidence
    fraud_investigator  -> fraud_score, fraud_signals, investigator_verdict
    policy_agent        -> decision, reason, refund_amount, requires_human_approval
    human_approval      -> approval_decision
    resolution_agent    -> customer_message
    refund/reject/escalate -> outcome
    (every node)        -> agent_messages (buffer), audit_trail (log)
"""
from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


def _append(existing: list, new: list) -> list:
    """Reducer that appends lists (used for buffers/logs)."""
    return (existing or []) + (new or [])


class DisputeState(TypedDict, total=False):
    # --- input ---
    dispute_id: str

    # --- loaded context (intake) ---
    dispute: dict[str, Any]
    transaction: dict[str, Any]
    customer: dict[str, Any]
    merchant: dict[str, Any]

    # --- supervisor / dynamic dispatch control ---
    next_agent: str            # which agent the supervisor picked
    triage_attempts: int       # bounds the low-confidence triage loop

    # --- triage agent ---
    category: str
    category_confidence: float

    # --- fraud investigator agent (tool-calling) ---
    fraud_score: float
    fraud_signals: list[str]
    investigator_verdict: str  # free-text verdict from the tool-loop agent

    # --- linear-pipeline fraud_check node (retry loop) ---
    fraud_check_attempts: int
    service_available: bool

    # --- policy agent ---
    decision: str              # AUTO_RESOLVE | AUTO_REJECT | ESCALATE
    reason: str
    refund_amount: float
    requires_human_approval: bool
    approval_decision: str

    # --- resolution agent ---
    customer_message: str

    # --- terminal ---
    outcome: str               # REFUNDED | REJECTED | ESCALATED

    # --- context handling: a shared BUFFER of inter-agent notes ---
    # Each agent appends a short line so later agents (and humans) can see the
    # "conversation" between agents. This is the multi-agent scratchpad.
    agent_messages: Annotated[list, _append]

    # --- audit log (append-only) ---
    audit_trail: Annotated[list, add]
