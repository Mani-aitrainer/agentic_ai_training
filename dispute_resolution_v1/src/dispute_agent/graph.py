"""Multi-agent graph assembly.

    START -> intake -> supervisor
                          |  (dynamic task allocation)
        +-----------------+---------------------+
        v                 v                     v
   triage_agent   fraud_investigator      policy_agent
        |                 |                     |
        +----> supervisor <----+               | (decision)
        (loops back until context gathered)     |
                                    +-----------+-----------+
                                    | AUTO_RESOLVE  ESCALATE|
                                    v                       v
                            (needs human?)             escalate
                              |        |                    |
                            human    refund                 |
                           approval    |                    |
                              |        v                    v
                              +--> resolution_agent <-------+
                                          |
                                          v
                                         END

Backward-compatible single-agent pipeline is still available via
``build_linear_graph`` (the original design) for teaching contrast.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from .agents.fraud_investigator import make_fraud_investigator
from .agents.specialists import (
    make_policy_agent,
    make_resolution_agent,
    make_supervisor,
    make_triage_agent,
)
from .dependencies import Dependencies, build_default_dependencies
from .nodes import make_nodes
from .routers import after_decide, after_fraud_check, supervisor_route
from .state import DisputeState
from .tools import bind_repository


# ---------------------------------------------------------------------------
# Original single-agent linear pipeline (kept for teaching contrast / tests).
# ---------------------------------------------------------------------------
def build_linear_graph(deps: Dependencies | None = None, *, checkpointer=None):
    if deps is None:
        deps = build_default_dependencies()
    nodes = make_nodes(deps)
    g = StateGraph(DisputeState)
    for name, fn in nodes.items():
        g.add_node(name, fn)
    g.add_edge(START, "intake")
    g.add_edge("intake", "classify")
    g.add_edge("classify", "fraud_check")
    g.add_conditional_edges(
        "fraud_check", after_fraud_check,
        {"fraud_check": "fraud_check", "decide": "decide", "escalate": "escalate"},
    )
    g.add_conditional_edges(
        "decide", after_decide,
        {"human_approval": "human_approval", "refund": "refund",
         "reject": "reject", "escalate": "escalate"},
    )
    g.add_edge("human_approval", "refund")
    g.add_edge("refund", END)
    g.add_edge("reject", END)
    g.add_edge("escalate", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())


# ---------------------------------------------------------------------------
# Multi-agent, supervisor-orchestrated graph (the enhanced design).
# ---------------------------------------------------------------------------
def build_graph(deps: Dependencies | None = None, *, checkpointer=None,
                fraud_model_factory=None):
    """Assemble the multi-agent dispute graph.

    fraud_model_factory(txn_id) -> chat model for the Fraud Investigator's tool
    loop. Defaults to the offline scripted model inside the agent; pass a
    factory returning ChatOpenAI for live tool-calling.
    """
    if deps is None:
        deps = build_default_dependencies()

    # Tools read from the same repository the rest of the system uses.
    bind_repository(deps.repo)

    nodes = make_nodes(deps)                       # reuse intake + terminal nodes
    supervisor = make_supervisor()
    triage_agent = make_triage_agent(deps.classifier)
    fraud_investigator = make_fraud_investigator(fraud_model_factory)
    policy_agent = make_policy_agent()
    resolution_agent = make_resolution_agent(deps.message_writer)

    g = StateGraph(DisputeState)

    # --- nodes ---
    g.add_node("intake", nodes["intake"])
    g.add_node("supervisor", supervisor)
    g.add_node("triage_agent", triage_agent)
    g.add_node("fraud_investigator", fraud_investigator)
    g.add_node("policy_agent", policy_agent)
    g.add_node("human_approval", nodes["human_approval"])
    g.add_node("refund", nodes["refund"])
    g.add_node("reject", nodes["reject"])
    g.add_node("escalate", nodes["escalate"])
    g.add_node("resolution_agent", resolution_agent)

    # --- spine ---
    g.add_edge(START, "intake")
    g.add_edge("intake", "supervisor")

    # --- dynamic dispatch out of the supervisor ---
    g.add_conditional_edges(
        "supervisor", supervisor_route,
        {
            "triage_agent": "triage_agent",
            "fraud_investigator": "fraud_investigator",
            "policy_agent": "policy_agent",
        },
    )

    # workers loop back to the supervisor for the next allocation
    g.add_edge("triage_agent", "supervisor")
    g.add_edge("fraud_investigator", "supervisor")

    # --- policy decision branch ---
    g.add_conditional_edges(
        "policy_agent", after_decide,
        {"human_approval": "human_approval", "refund": "refund",
         "reject": "reject", "escalate": "escalate"},
    )
    g.add_edge("human_approval", "refund")

    # --- terminal outcome nodes flow into the resolution agent ---
    g.add_edge("refund", "resolution_agent")
    g.add_edge("reject", "resolution_agent")
    g.add_edge("escalate", "resolution_agent")
    g.add_edge("resolution_agent", END)

    return g.compile(checkpointer=checkpointer or InMemorySaver())
