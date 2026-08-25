"""Tests that run without any API key - they exercise the stub LLM path."""

from support_agent.config import Settings
from support_agent.graph import build_graph, run_agent
from support_agent.tools import classify_priority, search_knowledge_base


def test_knowledge_base_hit():
    assert "5-7 business days" in search_knowledge_base.invoke({"query": "how long for a refund?"})


def test_knowledge_base_miss():
    assert search_knowledge_base.invoke({"query": "what is the meaning of life"}).startswith("NO_MATCH")


def test_priority_rules():
    assert classify_priority.invoke({"ticket_text": "total outage, nothing loads"}) == "P1"
    assert classify_priority.invoke({"ticket_text": "question about my invoice"}) == "P2"
    assert classify_priority.invoke({"ticket_text": "just saying hello"}) == "P3"


def test_graph_runs_without_api_key():
    settings = Settings(openai_api_key=None)
    result = run_agent("I was charged twice", graph=build_graph(settings), settings=settings)
    assert result["priority"] == "P1"
    assert "[stub-llm]" in result["reply"]
