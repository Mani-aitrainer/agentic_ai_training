"""Integration tests: the full compiled graph, end to end, offline.

These exercise the state machine as a whole -- routing, the retry loop, and the
human-in-the-loop interrupt/resume -- using stub dependencies.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from dispute_agent.agents.specialists import StubMessageWriter
from dispute_agent.classifier import StubClassifier
from dispute_agent.dependencies import Dependencies
from dispute_agent.fraud import FraudService
from dispute_agent.graph import build_graph, build_linear_graph


def _graph(deps):
    return build_graph(deps, checkpointer=InMemorySaver())


def _make_deps(repo, fraud_fails=0):
    return Dependencies(
        repo=repo,
        classifier=StubClassifier(),
        fraud_service=FraudService(fail_times=fraud_fails),
        message_writer=StubMessageWriter(),
    )


def test_duplicate_flows_to_refund(deps):
    graph = _graph(deps)
    out = graph.invoke({"dispute_id": "D_DUP"}, {"configurable": {"thread_id": "t1"}})
    assert out["category"] == "DUPLICATE"
    assert out["outcome"] == "REFUNDED"


def test_service_not_rendered_escalates(deps):
    graph = _graph(deps)
    out = graph.invoke({"dispute_id": "D_SNR"}, {"configurable": {"thread_id": "t2"}})
    assert out["category"] == "SERVICE_NOT_RENDERED"
    assert out["outcome"] == "ESCALATED"


def test_high_value_fraud_pauses_for_human_then_refunds(deps):
    graph = _graph(deps)
    config = {"configurable": {"thread_id": "t3"}}
    paused = graph.invoke({"dispute_id": "D_FRAUD"}, config)
    # graph should have paused at the human gate
    assert "__interrupt__" in paused
    payload = paused["__interrupt__"][0].value
    assert payload["amount"] == 65000.0
    # officer approves -> refund
    final = graph.invoke(Command(resume="yes"), config)
    assert final["outcome"] == "REFUNDED"


def test_high_value_fraud_officer_rejects(deps):
    graph = _graph(deps)
    config = {"configurable": {"thread_id": "t4"}}
    graph.invoke({"dispute_id": "D_FRAUD"}, config)
    final = graph.invoke(Command(resume="no"), config)
    assert final["outcome"] == "REJECTED"


def test_retry_loop_recovers_after_transient_outage(repo):
    # The fraud-service retry loop is a feature of the linear pipeline.
    deps = _make_deps(repo, fraud_fails=2)
    graph = build_linear_graph(deps, checkpointer=InMemorySaver())
    out = graph.invoke({"dispute_id": "D_DUP"}, {"configurable": {"thread_id": "t5"}})
    assert out["outcome"] == "REFUNDED"
    assert out["fraud_check_attempts"] == 3


def test_retry_exhaustion_escalates(repo):
    deps = _make_deps(repo, fraud_fails=99)
    graph = build_linear_graph(deps, checkpointer=InMemorySaver())
    out = graph.invoke({"dispute_id": "D_DUP"}, {"configurable": {"thread_id": "t6"}})
    assert out["outcome"] == "ESCALATED"


def test_audit_trail_accumulates(deps):
    graph = _graph(deps)
    out = graph.invoke({"dispute_id": "D_DUP"}, {"configurable": {"thread_id": "t7"}})
    trail = out["audit_trail"]
    # every stage should have written at least one line
    assert any("intake" in line for line in trail)
    assert any("supervisor" in line for line in trail)
    assert any("triage_agent" in line for line in trail)
    assert any("policy_agent" in line for line in trail)
