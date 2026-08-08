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