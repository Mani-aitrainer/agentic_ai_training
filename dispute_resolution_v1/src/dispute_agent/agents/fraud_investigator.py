"""Fraud Investigator Agent -- a tool-calling agent embedded as a graph node.

This is the "LangChain tools inside LangGraph" + "full tool loop" concept.
The agent is itself a small subgraph:  agent <-> tools  looping until the model
stops requesting tools. We run that subgraph inside a single node of the parent
graph, then write the extracted results back into the parent's shared state.

Offline, a ScriptedToolModel drives the identical loop with no API key.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from ..config import settings
from ..prompts import FRAUD_INVESTIGATOR_SYSTEM, fraud_investigator_kickoff
from ..scratchpad import note
from ..state import DisputeState
from ..tools import FRAUD_INVESTIGATION_TOOLS
from .scripted_model import scripted_investigator


def _build_tool_loop(model):
    """Build the agent<->tools loop subgraph for a given (already tool-bound) model."""
    bound = model.bind_tools(FRAUD_INVESTIGATION_TOOLS)

    def call_model(state: MessagesState) -> dict:
        return {"messages": [bound.invoke(state["messages"])]}

    sub = StateGraph(MessagesState)
    sub.add_node("investigator", call_model)
    sub.add_node("tools", ToolNode(FRAUD_INVESTIGATION_TOOLS))
    sub.add_edge(START, "investigator")
    # tools_condition routes to "tools" if the model asked for a tool, else END
    sub.add_conditional_edges("investigator", tools_condition, {"tools": "tools", END: END})
    sub.add_edge("tools", "investigator")
    return sub.compile()


def _extract_signals(messages: list) -> tuple[float, list[str]]:
    """Pull the fraud score/signals out of the compute_fraud_signals tool result.

    ToolNode serialises a tool's dict return value to a JSON string in the
    ToolMessage content, so we parse the JSON. We scan the newest tool result
    first so a re-investigation supersedes an earlier one.
    """
    for m in reversed(messages):
        if isinstance(m, ToolMessage) and "fraud_score" in str(m.content):
            try:
                data = json.loads(m.content)
            except (json.JSONDecodeError, TypeError):
                continue
            return float(data.get("fraud_score", 0.0)), list(data.get("signals", []))
    return 0.0, []


def make_fraud_investigator(model_factory: Callable[[str], Any] | None = None):
    """Return the parent-graph node function.

    model_factory(txn_id) -> a chat model. Defaults to the offline scripted
    model; pass a factory returning ChatOpenAI for live investigation.
    """

    def fraud_investigator(state: DisputeState) -> dict[str, Any]:
        txn_id = state["transaction"]["txn_id"]
        factory = model_factory or scripted_investigator
        model = factory(txn_id)
        loop = _build_tool_loop(model)

        kickoff = [
            SystemMessage(content=FRAUD_INVESTIGATOR_SYSTEM),
            HumanMessage(content=fraud_investigator_kickoff(txn_id, state.get("category", "?"))),
        ]
        result = loop.invoke({"messages": kickoff})

        score, signals = _extract_signals(result["messages"])
        verdict_msg = next(
            (m for m in reversed(result["messages"])
             if isinstance(m, AIMessage) and m.content and not m.tool_calls),
            None,
        )
        verdict = verdict_msg.content if verdict_msg else "no verdict"
        strong = score >= settings.fraud_score_threshold

        return {
            "fraud_score": score,
            "fraud_signals": signals,
            "investigator_verdict": verdict,
            "service_available": True,
            "agent_messages": [
                note(
                    "fraud_investigator",
                    f"score={score}, signals={signals}, "
                    f"evidence={'STRONG' if strong else 'WEAK'}",
                )
            ],
            "audit_trail": [
                f"fraud_investigator: tool-loop done, score={score}, "
                f"signals={signals} (tool calls in {len(result['messages'])} msgs)"
            ],
        }

    return fraud_investigator
