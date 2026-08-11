"""Conditional-edge routers.

These are the transition functions of the state machine. Each is a pure
function of state -> next-node-name, which makes them the easiest components
in the whole project to unit test: feed a dict, assert a string.
"""
from __future__ import annotations

from .config import settings
from .state import DisputeState


def after_fraud_check(state: DisputeState) -> str:
    """Retry loop: if the fraud service was down, try again up to the limit,
    then give up and escalate. Otherwise move on to the decision."""
    if state.get("service_available"):
        return "decide"
    if state.get("fraud_check_attempts", 0) >= settings.max_fraud_check_attempts:
        return "escalate"
    return "fraud_check"  # loop back and retry


def after_decide(state: DisputeState) -> str:
    """Three-way branch: resolve (maybe via a human gate), reject, or escalate."""
    decision = state.get("decision")
    if decision == "AUTO_RESOLVE":
        return "human_approval" if state.get("requires_human_approval") else "refund"
    if decision == "AUTO_REJECT":
        return "reject"
    return "escalate"


def supervisor_route(state: DisputeState) -> str:
    """Dynamic dispatch: send control to whichever agent the supervisor chose.

    The supervisor node writes ``next_agent`` into state; this transition simply
    reads it. Keeping the *decision* (supervisor node) separate from the
    *transition* (this function) is the clean way to unit-test dispatch logic.
    """
    return state["next_agent"]
