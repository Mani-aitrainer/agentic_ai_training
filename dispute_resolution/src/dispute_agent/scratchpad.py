"""Helpers for the shared inter-agent buffer.

The buffer (``state['agent_messages']``) is how agents leave notes for each
other and for the human reviewer -- a lightweight, structured conversation
log that travels in the graph state. Kept tiny on purpose.
"""
from __future__ import annotations


def note(agent: str, message: str) -> dict[str, str]:
    """Build one buffer entry. Returned inside a list so the state reducer appends it."""
    return {"agent": agent, "message": message}


def render_buffer(agent_messages: list[dict[str, str]]) -> str:
    """Render the buffer as text an agent can be shown as context."""
    if not agent_messages:
        return "(no prior agent notes)"
    return "\n".join(f"[{m['agent']}] {m['message']}" for m in agent_messages)
