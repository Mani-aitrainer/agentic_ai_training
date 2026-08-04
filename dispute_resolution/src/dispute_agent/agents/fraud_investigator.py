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
