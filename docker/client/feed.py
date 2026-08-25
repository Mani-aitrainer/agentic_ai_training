"""Ticket feeder - the container-to-container communication demo.

Run it with:  docker compose --profile demo up feeder

What it demonstrates
--------------------
1. DNS on a user-defined bridge network. `http://agent:8000` resolves because
   Compose registers every service name in the network's embedded DNS server.
   Try changing AGENT_URL to `http://localhost:8000` and watch it fail:
   inside a container, localhost is THAT container, not your laptop.
2. Port 8000 here is the CONTAINER port, not the published one. Container-to-
   container traffic never goes through the `ports:` mapping at all - you could
   delete `ports:` from the agent service entirely and this would still work.
3. Startup ordering. `depends_on: service_healthy` means the agent is already
   answering /healthz before this process gets its first CPU cycle.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

AGENT_URL = os.getenv("AGENT_URL", "http://localhost/:8000").rstrip("/")
TICKETS = [
    "I was charged twice this month, please refund me",
    "How long does standard shipping take?",
    "I cannot login and the whole site is down",
    "Where do I download last month's invoice?",
    "I forgot my password, how do I reset it?",
]


def wait_for_agent(timeout: int = 60) -> None:
    """Belt-and-braces retry loop.

    Compose's healthcheck already gates us, but a real system must never assume
    a dependency is up. Retrying beats crashing: 'the network is reliable' is
    the first fallacy of distributed computing.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{AGENT_URL}/healthz", timeout=3) as r:
                if r.status == 200:
                    print(f"[feeder] agent reachable at {AGENT_URL}", flush=True)
                    return
        except urllib.error.URLError as exc:
            print(f"[feeder] waiting for {AGENT_URL} ({exc.reason})", flush=True)
        time.sleep(2)
    sys.exit(f"[feeder] agent never became healthy at {AGENT_URL}")


def ask(ticket: str) -> dict:
    body = json.dumps({"message": ticket, "session_id": "feeder"}).encode()
    req = urllib.request.Request(
        f"{AGENT_URL}/chat", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> None:
    wait_for_agent()
    for ticket in TICKETS:
        answer = ask(ticket)
        print(
            f"[feeder] {answer['priority']}  tools={answer['tools_used'] or '-'}  "
            f"| {ticket}\n         -> {answer['reply'][:110]}",
            flush=True,
        )
        time.sleep(1)

    # Read the shared counter back. Because the agent writes it to the Redis
    # CONTAINER, this total survives `docker compose restart agent`.
    with urllib.request.urlopen(f"{AGENT_URL}/metrics", timeout=5) as r:
        print(f"[feeder] done.\n{r.read().decode()}", flush=True)


if __name__ == "__main__":
    main()
