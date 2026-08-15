"""Team assembly -- wiring the agents into a collaborating group.

This is "building helper agents and supervisor agents". The Researcher and
Writer are helper agents; the Critic acts as the supervisor that decides when
the work is done (by emitting APPROVE). ``RoundRobinGroupChat`` is the
coordinator: agents take turns in order and share one conversation context.

The termination condition -- APPROVE mentioned OR a hard message cap -- is the
safety valve that guarantees the loop ends (an "edge case" from Section 9).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat

from .agents import build_critic, build_researcher, build_writer
from .config import settings
from .model_client import build_openai_client, build_replay_client
from .tools import stub_web_search, web_search


@dataclass
class ReportResult:
    """Structured outcome of a team run."""
    report: str
    approved: bool
    rounds: int
    stop_reason: str
    transcript: list[tuple[str, str]]  # (agent_name, message) in order


def _termination():
    """APPROVE ends it; the message cap is the backstop against infinite loops."""
    return TextMentionTermination(settings.approve_word) | MaxMessageTermination(
        settings.max_messages
    )


def build_team(model_clients: dict, *, offline: bool):
    """Assemble the RoundRobinGroupChat.

    model_clients: {"researcher": client, "writer": client, "critic": client}
    offline: when True the Researcher gets the deterministic stub search tool.
    """
    search_tool = stub_web_search if offline else web_search
    researcher = build_researcher(model_clients["researcher"], tools=[search_tool])
    writer = build_writer(model_clients["writer"])
    critic = build_critic(model_clients["critic"])

    return RoundRobinGroupChat(
        [researcher, writer, critic],
        termination_condition=_termination(),
    )


# --- Convenience builders for the two run modes -----------------------------

def build_live_team():
    """Real OpenAI-backed team (needs OPENAI_API_KEY)."""
    clients = {
        "researcher": build_openai_client(),
        "writer": build_openai_client(),
        "critic": build_openai_client(),
    }
    return build_team(clients, offline=False)


def build_offline_team(
    researcher_lines: Sequence[str],
    writer_lines: Sequence[str],
    critic_lines: Sequence[str],
):
    """Offline team driven by scripted replay clients (no API key)."""
    clients = {
        "researcher": build_replay_client(researcher_lines),
        "writer": build_replay_client(writer_lines),
        "critic": build_replay_client(critic_lines),
    }
    return build_team(clients, offline=True)


def default_offline_script(topic: str):
    """A canned two-round conversation used by the offline demo and tests.

    Round 1: research -> draft -> REVISE.  Round 2: research -> draft -> APPROVE.
    Each agent needs one line per round it speaks in.
    """
    researcher_lines = [
        f"Research brief v1 on '{topic}': key points gathered from sources.",
        f"Research brief v2 on '{topic}': added a comparison table and 2026 context.",
    ]
    writer_lines = [
        f"# {topic}\n\nDRAFT v1: introduction and overview only.",
        (f"# {topic}\n\nDRAFT v2:\n\n## Overview\n...\n\n## Comparison\n"
         "| A | B |\n|---|---|\n\n## When to use which\n..."),
    ]
    critic_lines = [
        f"Missing a comparison table and a 'when to use' section. {settings.revise_word}",
        f"Accurate, complete, and well structured. {settings.approve_word}",
    ]
    return researcher_lines, writer_lines, critic_lines
