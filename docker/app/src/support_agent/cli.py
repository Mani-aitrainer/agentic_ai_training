"""Local dev entrypoint: `python -m support_agent.cli "my question"`.

Useful before you containerise anything - Section 15's "local dev + container
testing" point is exactly this: prove the code works on the host first, then
prove the *image* works, then prove the *cluster* works.
"""

from __future__ import annotations

import argparse
import json
import sys

from .config import get_settings
from .graph import build_graph, run_agent
from .logging_config import configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the support triage agent a question.")
    parser.add_argument("message", nargs="*", help="The customer message.")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON.")
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level)

    message = " ".join(args.message).strip()
    if not message:
        message = input("Customer message: ").strip()
    if not message:
        print("Nothing to do.", file=sys.stderr)
        return 1

    result = run_agent(message, graph=build_graph(settings))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nPriority : {result['priority']}")
        print(f"Tools    : {', '.join(result['tools_used']) or '(none)'}")
        print(f"Reply    : {result['reply']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
