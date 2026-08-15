"""The three specialist agents and their roles.

This module is where "defining roles and communication protocols" lives.

Communication protocol (the contract the agents share):
  * The Researcher gathers facts (optionally via the web_search tool) and hands
    a factual brief to the team.
  * The Writer turns the latest brief + critique into a full report draft.
  * The Critic reviews the draft. It MUST end its message with exactly one
    sentinel:
        - "REVISE" + specific, actionable feedback  -> triggers another round
        - "APPROVE"                                  -> ends the conversation
    The team's termination condition watches for "APPROVE".

Each agent is built by a factory that takes a model client, so we can inject a
real OpenAI client or an offline replay client without changing the roles.
"""
from __future__ import annotations

from typing import Callable

from autogen_agentchat.agents import AssistantAgent

from .config import settings

# --- System prompts: one narrow role each (modular prompt engineering) --------

RESEARCHER_SYSTEM = (
    "You are the Researcher on a report-writing team. Your ONLY job is to gather "
    "accurate, relevant facts about the requested topic. If a web_search tool is "
    "available, use it to find current information, then summarise the key facts "
    "as a concise, bulleted research brief with any figures and sources. "
    "Do not write the final report -- that is the Writer's job. Hand off a clean "
    "brief the Writer can use."
)

def build_researcher(model_client, tools: list[Callable] | None = None) -> AssistantAgent:
    """The Researcher. Pass tools=[web_search] to give it live search."""
    return AssistantAgent(
        name="researcher",
        model_client=model_client,
        tools=tools or [],
        system_message=RESEARCHER_SYSTEM,
        description="Gathers facts about the topic, optionally via web search.",
    )


WRITER_SYSTEM = (
    "You are the Writer on a report-writing team. Using the Researcher's brief "
    "and any feedback from the Critic, write a clear, well-structured report on "
    "the topic. Use short sections and plain language. When the Critic asks for "
    "changes, revise the WHOLE report and present the full updated version, not "
    "just the changes. Do not evaluate your own work -- the Critic does that."
)

def build_writer(model_client) -> AssistantAgent:
    """The Writer. Turns briefs + critique into a full report draft."""
    return AssistantAgent(
        name="writer",
        model_client=model_client,
        system_message=WRITER_SYSTEM,
        description="Writes and revises the report from the research brief.",
    )


def critic_system() -> str:
    return (
        "You are the Critic on a report-writing team. Review the Writer's latest "
        "draft for accuracy, completeness, structure, and clarity. Be specific.\n"
        f"If the draft needs work, reply with concrete, actionable feedback and end "
        f"your message with the single word {settings.revise_word}.\n"
        f"If the draft is genuinely good, reply with a one-line reason and end your "
        f"message with the single word {settings.approve_word}.\n"
        f"End every message with exactly one of: {settings.approve_word} or "
        f"{settings.revise_word}."
    )


# --- Agent factories ----------------------------------------------------------
def build_critic(model_client) -> AssistantAgent:
    """The Critic. Gate-keeps quality; emits APPROVE or REVISE."""
    return AssistantAgent(
        name="critic",
        model_client=model_client,
        system_message=critic_system(),
        description="Reviews drafts and decides APPROVE or REVISE.",
    )
