"""The LangGraph agent.

    START -> agent -> (tools -> agent)* -> finalise -> END

`agent`    calls the LLM, which may ask for a tool call.
`tools`    executes whatever the LLM asked for and feeds the result back.
`finalise` stamps a priority on the ticket so the API always has one.

The whole graph is compiled once at import time and reused for every request -
compiling per request would waste CPU on every container.
"""

from __future__ import annotations

import logging
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from .config import Settings, get_settings
from .llm import build_llm
from .tools import TOOLS_BY_NAME, classify_priority

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a customer-support triage agent. Use search_knowledge_base to find "
    "an answer and classify_priority to grade urgency. Answer in at most three "
    "sentences. If the knowledge base has no match, say so plainly and suggest "
    "escalating to a human."
)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    tools_used: list[str]
    priority: str
    iterations: int


def _agent_node(state: AgentState, llm) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response], "iterations": state.get("iterations", 0) + 1}


def _tools_node(state: AgentState) -> dict:
    last = state["messages"][-1]
    outputs: list[BaseMessage] = []
    used: list[str] = []
    for call in getattr(last, "tool_calls", []) or []:
        tool = TOOLS_BY_NAME.get(call["name"])
        if tool is None:
            result = f"ERROR: unknown tool {call['name']}"
        else:
            try:
                result = tool.invoke(call["args"])
            except Exception as exc:  # noqa: BLE001 - never kill the container on a tool bug
                log.exception("tool %s failed", call["name"])
                result = f"ERROR: {exc}"
        used.append(call["name"])
        outputs.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return {"messages": outputs, "tools_used": used}


def _finalise_node(state: AgentState) -> dict:
    first_user = next(
        (m.content for m in state["messages"] if isinstance(m, HumanMessage)), ""
    )
    return {"priority": classify_priority.invoke({"ticket_text": str(first_user)})}


def _should_continue(state: AgentState, max_iterations: int) -> str:
    last = state["messages"][-1]
    if state.get("iterations", 0) >= max_iterations:
        return "finalise"
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "finalise"


def build_graph(settings: Settings | None = None):
    settings = settings or get_settings()
    llm = build_llm(settings)

    builder = StateGraph(AgentState)
    builder.add_node("agent", lambda state: _agent_node(state, llm))
    builder.add_node("tools", _tools_node)
    builder.add_node("finalise", _finalise_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        lambda state: _should_continue(state, settings.max_tool_iterations),
        {"tools": "tools", "finalise": "finalise"},
    )
    builder.add_edge("tools", "agent")
    builder.add_edge("finalise", END)
    return builder.compile()


def run_agent(message: str, graph=None, settings: Settings | None = None) -> dict:
    """Single-shot helper shared by the HTTP API and the CLI."""
    settings = settings or get_settings()
    graph = graph or build_graph(settings)
    final = graph.invoke(
        {
            "messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=message)],
            "tools_used": [],
            "priority": "P3",
            "iterations": 0,
        }
    )
    reply = next(
        (m.content for m in reversed(final["messages"]) if isinstance(m, AIMessage) and m.content),
        "No answer produced.",
    )
    return {
        "reply": str(reply),
        "priority": final.get("priority", "P3"),
        "tools_used": final.get("tools_used", []),
    }
