"""Host-side client for the Support Triage Agent.

The feeder in client/feed.py talks to the agent from INSIDE the Docker network
(http://agent:8000). This script is the other half of the story: it talks to the
agent from your laptop, through the published port (http://localhost:8000).

    python consume_agent.py health
    python consume_agent.py chat "I was charged twice, I need a refund"
    python consume_agent.py batch
    python consume_agent.py repl
    python consume_agent.py metrics

Point it somewhere else with --url or the AGENT_URL env var:

    python consume_agent.py --url http://localhost:8001 health
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import requests

DEFAULT_URL = os.getenv("AGENT_URL", "http://localhost:8000")

SAMPLE_TICKETS = [
    "I was charged twice this month, please refund me",
    "How long does standard shipping take?",
    "I cannot login and the whole site is down",
    "Where do I download last month's invoice?",
    "I forgot my password, how do I reset it?",
]


class AgentClient:
    """A thin wrapper over the agent's HTTP surface.

    One requests.Session is reused for every call so the TCP connection is kept
    alive - it matters the moment you send more than a couple of tickets.
    """

    def __init__(self, base_url: str = DEFAULT_URL, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ---------------------------------------------------------------- ops ---
    def health(self) -> dict:
        """GET /healthz - liveness. Never touches the LLM."""
        r = self.session.get(f"{self.base_url}/healthz", timeout=5)
        r.raise_for_status()
        return r.json()

    def ready(self) -> bool:
        """GET /readyz - 503 until the graph is compiled and the store is up."""
        return self.session.get(f"{self.base_url}/readyz", timeout=5).status_code == 200

    def metrics(self) -> str:
        """GET /metrics - the Redis-backed request counter, Prometheus format."""
        r = self.session.get(f"{self.base_url}/metrics", timeout=5)
        r.raise_for_status()
        return r.text

    def wait_until_ready(self, timeout: int = 60) -> None:
        """Never assume a dependency is up. Retry, don't crash."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self.ready():
                    return
            except requests.RequestException as exc:
                print(f"  waiting for {self.base_url} ({exc.__class__.__name__})")
            time.sleep(2)
        sys.exit(f"agent never became ready at {self.base_url}")

    # -------------------------------------------------------------- agent ---
    def chat(self, message: str, session_id: str | None = None) -> dict:
        """POST /chat - the actual work. Returns reply/priority/tools_used."""
        payload = {"message": message, "session_id": session_id}
        r = self.session.post(f"{self.base_url}/chat", json=payload, timeout=self.timeout)
        if r.status_code == 422:                      # pydantic rejected the body
            raise ValueError(f"invalid request: {r.json()['detail']}")
        if r.status_code == 502:                      # the graph itself blew up
            raise RuntimeError(f"agent error: {r.json()['detail']}")
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "AgentClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


# --------------------------------------------------------------------------
# Presentation
# --------------------------------------------------------------------------
def show(ticket: str, answer: dict) -> None:
    tools = ", ".join(answer["tools_used"]) or "-"
    print(f"\n  ticket   {ticket}")
    print(f"  priority {answer['priority']}   tools: {tools}")
    print(f"  reply    {answer['reply']}")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def cmd_health(client: AgentClient, _: argparse.Namespace) -> None:
    info = client.health()
    print(f"status      {info['status']}")
    print(f"version     {info['version']}")
    print(f"environment {info['environment']}")
    print(f"llm         {info['llm']}      # 'stub' means no OPENAI_API_KEY reached the container")
    print(f"ready       {client.ready()}")


def cmd_chat(client: AgentClient, args: argparse.Namespace) -> None:
    show(args.message, client.chat(args.message, session_id=args.session))


def cmd_batch(client: AgentClient, args: argparse.Namespace) -> None:
    client.wait_until_ready()
    tickets = args.tickets or SAMPLE_TICKETS
    for ticket in tickets:
        show(ticket, client.chat(ticket, session_id=args.session))
    print(f"\n{client.metrics()}")


def cmd_metrics(client: AgentClient, _: argparse.Namespace) -> None:
    print(client.metrics())


def cmd_repl(client: AgentClient, args: argparse.Namespace) -> None:
    print(f"connected to {client.base_url}  (blank line or Ctrl-C to quit)")
    while True:
        try:
            message = input("\nticket> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not message:
            return
        try:
            show(message, client.chat(message, session_id=args.session))
        except (ValueError, RuntimeError, requests.RequestException) as exc:
            print(f"  ! {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=DEFAULT_URL, help=f"agent base URL (default {DEFAULT_URL})")
    parser.add_argument("--session", default="host-client", help="session_id sent with each /chat")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="liveness + readiness + which LLM is wired up").set_defaults(fn=cmd_health)
    sub.add_parser("metrics", help="the Redis-backed request counter").set_defaults(fn=cmd_metrics)
    sub.add_parser("repl", help="interactive prompt").set_defaults(fn=cmd_repl)

    p_chat = sub.add_parser("chat", help="send one ticket")
    p_chat.add_argument("message")
    p_chat.set_defaults(fn=cmd_chat)

    p_batch = sub.add_parser("batch", help="send several tickets, then read the counter")
    p_batch.add_argument("tickets", nargs="*", help="defaults to the 5 built-in samples")
    p_batch.set_defaults(fn=cmd_batch)

    args = parser.parse_args()
    try:
        with AgentClient(args.url) as client:
            args.fn(client, args)
    except requests.ConnectionError:
        sys.exit(f"cannot reach {args.url} - is the stack up? (docker compose ps)")
    except (ValueError, RuntimeError) as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
