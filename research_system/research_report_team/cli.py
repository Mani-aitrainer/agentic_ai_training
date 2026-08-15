"""Command-line runner.

Examples:
    # Offline: run the AutoGen team alone (no API key), stream the conversation:
    python cli.py --topic "LangGraph vs AutoGen" --offline

    # Offline: run the full LangGraph-orchestrated workflow with the human gate:
    python cli.py --topic "LangGraph vs AutoGen" --offline --graph --approve yes

    # Live (needs OPENAI_API_KEY): real research team with web search:
    python cli.py --topic "State of AI agents in 2026"
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from langgraph.types import Command

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from research_team.runner import run_team  # noqa: E402
from research_team.team import (  # noqa: E402
    build_live_team,
    build_offline_team,
    default_offline_script,
)


def run_team_only(topic: str, offline: bool) -> None:
    if offline:
        team = build_offline_team(*default_offline_script(topic))
    else:
        team = build_live_team()
    result = asyncio.run(run_team(team, topic))

    print(f"\n=== Conversation on: {topic} ===")
    for source, text in result.transcript:
        print(f"\n[{source}]\n{text}")
    print(f"\n--- approved={result.approved} rounds={result.rounds} "
          f"stop_reason={result.stop_reason!r} ---")
    print("\n=== FINAL REPORT ===\n")
    print(result.report)


def main() -> None:
    p = argparse.ArgumentParser(description="Research & Report Writing Team (AutoGen + LangGraph)")
    p.add_argument("--topic", required=True, help="What to write a report about")
    p.add_argument("--offline", action="store_true", help="Use scripted replay models (no API key)")
    p.add_argument("--approve", choices=["yes", "no"], default=None, help="Auto-answer the human gate")
    args = p.parse_args()
    run_team_only(args.topic, args.offline)


if __name__ == "__main__":
    main()
