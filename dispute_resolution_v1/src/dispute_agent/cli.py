"""Command-line runner for the multi-agent dispute resolution agent.

Examples:
    # Run every dispute through the MULTI-AGENT graph, fully offline:
    python cli.py --all --offline

    # One case, offline, auto-approving the human gate, showing the agent buffer:
    python cli.py --dispute DSP003 --offline --approve yes --show-buffer

    # Contrast with the original single-agent LINEAR pipeline:
    python cli.py --dispute DSP003 --offline --linear --approve yes

    # Simulate the fraud service failing (linear pipeline retry loop):
    python cli.py --dispute DSP001 --offline --linear --fraud-fails 2

    # Real OpenAI (needs OPENAI_API_KEY): live triage, live tool-calling
    # investigator, live customer message:
    python cli.py --dispute DSP003
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from langgraph.types import Command

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dispute_agent.data_access import JsonRepository  # noqa: E402
from dispute_agent.dependencies import (  # noqa: E402
    build_default_dependencies,
    build_offline_dependencies,
)
from dispute_agent.graph import build_graph, build_linear_graph  # noqa: E402
from dispute_agent.scratchpad import render_buffer  # noqa: E402


def make_graph(offline: bool, linear: bool, fraud_fails: int):
    deps = build_offline_dependencies(fraud_fails=fraud_fails) if offline else build_default_dependencies()
    builder = build_linear_graph if linear else build_graph
    # For the live multi-agent path, wire a real tool-calling model factory.
    if not offline and not linear:
        from langchain_openai import ChatOpenAI

        from dispute_agent.config import settings

        def factory(_txn_id):
            return ChatOpenAI(model=settings.openai_model, temperature=0.0)

        return build_graph(deps, fraud_model_factory=factory)
    return builder(deps)


def run_one(graph, dispute_id, auto_approve):
    config = {"configurable": {"thread_id": dispute_id}}
    result = graph.invoke({"dispute_id": dispute_id}, config)
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print(f"\n  PAUSE  human approval needed for {dispute_id}: "
              f"Rs.{payload['amount']} - {payload['reason']}")
        answer = auto_approve if auto_approve is not None else (input("     approve? [yes/no]: ").strip() or "no")
        if auto_approve is not None:
            print(f"     officer (auto): {answer}")
        result = graph.invoke(Command(resume=answer), config)
    return result


def print_result(dispute_id, result, show_buffer):
    print(f"\n=== {dispute_id} ===")
    print(f"category : {result.get('category')} (conf={result.get('category_confidence')})")
    if result.get("fraud_score") is not None:
        print(f"fraud    : score={result.get('fraud_score')} signals={result.get('fraud_signals')}")
    print(f"decision : {result.get('decision')}  ->  OUTCOME: {result.get('outcome')}")
    if result.get("customer_message"):
        print(f"message  : {result['customer_message']}")
    if show_buffer:
        print("agent buffer:")
        print("   " + render_buffer(result.get("agent_messages", [])).replace("\n", "\n   "))


def main():
    p = argparse.ArgumentParser(description="Dispute & Chargeback Resolution Agent (multi-agent)")
    p.add_argument("--dispute", help="A single dispute id, e.g. DSP001")
    p.add_argument("--all", action="store_true", help="Run every dispute in the mock data")
    p.add_argument("--offline", action="store_true", help="Use stub agents (no API key)")
    p.add_argument("--linear", action="store_true", help="Use the original single-agent pipeline")
    p.add_argument("--fraud-fails", type=int, default=0, help="Simulate N fraud-service outages (linear)")
    p.add_argument("--approve", choices=["yes", "no"], default=None, help="Auto-answer the human gate")
    p.add_argument("--show-buffer", action="store_true", help="Print the inter-agent buffer")
    args = p.parse_args()

    repo = JsonRepository()
    if args.all:
        dispute_ids = repo.list_dispute_ids()
    elif args.dispute:
        dispute_ids = [args.dispute]
    else:
        p.error("provide --dispute <id> or --all")

    mode = "LINEAR" if args.linear else "MULTI-AGENT"
    print(f"[{mode} pipeline | {'offline' if args.offline else 'openai'}]")

    for did in dispute_ids:
        graph = make_graph(args.offline, args.linear, args.fraud_fails)
        result = run_one(graph, did, args.approve)
        print_result(did, result, args.show_buffer)


if __name__ == "__main__":
    main()
