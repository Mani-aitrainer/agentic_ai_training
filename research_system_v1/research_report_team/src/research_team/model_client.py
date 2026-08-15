"""Model client factory.

AutoGen agents talk to an LLM through a *model client*. We expose two:

* ``build_openai_client()`` -- the real gpt-4.1-mini client (needs an API key).
* ``build_replay_client(scripted)`` -- an offline client that replays a list of
  canned strings, so the whole team runs in class with no key.

Both satisfy the same interface, so the agents and the team never know which
one they're using. That's the seam that makes this project demo-able offline
and testable without network.
"""
from __future__ import annotations

from typing import Sequence

from autogen_core.models import ModelInfo

from .config import settings

# model_info that advertises the capabilities our agents need (notably tool /
# function calling). The real OpenAI client fills this in itself; the replay
# client needs to be told, or AutoGen refuses to attach tools to the agent.
OFFLINE_MODEL_INFO = ModelInfo(
    vision=False,
    function_calling=True,
    json_output=True,
    family="unknown",
    structured_output=True,
    multiple_system_messages=True,
)


def build_openai_client(model: str | None = None):
    """The production model client (OpenAI gpt-4.1-mini by default)."""
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    return OpenAIChatCompletionClient(
        model=model or settings.openai_model,
        temperature=settings.temperature,
    )


def build_replay_client(scripted: Sequence[str]):
    """An offline client that replays ``scripted`` responses in order."""
    from autogen_ext.models.replay import ReplayChatCompletionClient

    return ReplayChatCompletionClient(list(scripted), model_info=OFFLINE_MODEL_INFO)
