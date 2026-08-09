"""Tests for context handling: the shared buffer and multi-agent coordination."""
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from dispute_agent.graph import build_graph
from dispute_agent.scratchpad import note, render_buffer


# --- the buffer helper + reducer ---
def test_note_shape():
    n = note("triage", "hello")
    assert n == {"agent": "triage", "message": "hello"}


def test_render_buffer_formats_lines():
    text = render_buffer([note("a", "one"), note("b", "two")])
    assert "[a] one" in text and "[b] two" in text


def test_render_empty_buffer():
    assert "no prior" in render_buffer([])


# --- the buffer accumulates across agents in a real run ---
def _graph(deps):
    return build_graph(deps, checkpointer=InMemorySaver())


def test_buffer_accumulates_across_agents(deps):
    graph = _graph(deps)
    out = graph.invoke({"dispute_id": "D_DUP"}, {"configurable": {"thread_id": "b1"}})
    agents_seen = {m["agent"] for m in out["agent_messages"]}
    # supervisor + triage + policy + resolution all leave notes on a duplicate
    assert {"supervisor", "triage", "policy", "resolution"} <= agents_seen


def test_fraud_case_includes_investigator_note(deps):
    graph = _graph(deps)
    cfg = {"configurable": {"thread_id": "b2"}}
    graph.invoke({"dispute_id": "D_FRAUD"}, cfg)
    out = graph.invoke(Command(resume="yes"), cfg)
    agents_seen = {m["agent"] for m in out["agent_messages"]}
    assert "fraud_investigator" in agents_seen


def test_memory_isolated_by_thread(deps):
    """Two dispute ids on different threads don't bleed state into each other."""
    graph = _graph(deps)
    a = graph.invoke({"dispute_id": "D_DUP"}, {"configurable": {"thread_id": "tA"}})
    b = graph.invoke({"dispute_id": "D_SNR"}, {"configurable": {"thread_id": "tB"}})
    assert a["category"] == "DUPLICATE"
    assert b["category"] == "SERVICE_NOT_RENDERED"
