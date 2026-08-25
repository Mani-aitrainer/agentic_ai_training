"""LLM factory with an offline fallback.

Why the fallback matters for this session: the container health check must be
able to pass without a live API key, otherwise every student without a funded
OpenAI account watches their container restart-loop instead of learning Docker.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage

from .config import Settings
from .tools import ALL_TOOLS

log = logging.getLogger(__name__)


class StubChatModel:
    """Deterministic stand-in used when OPENAI_API_KEY is not set."""

    def bind_tools(self, tools: Sequence[Any]) -> "StubChatModel":  # noqa: ARG002
        return self

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        last = messages[-1].content if messages else ""
        return AIMessage(
            content=(
                "[stub-llm] No OPENAI_API_KEY configured, so this is a canned reply. "
                f"I received: {last!r}"
            )
        )


def build_llm(settings: Settings):
    if not settings.llm_enabled:
        log.warning("OPENAI_API_KEY missing - falling back to StubChatModel")
        return StubChatModel()

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.model_name,
        temperature=settings.temperature,
        timeout=settings.request_timeout,
        api_key=settings.openai_api_key,
    ).bind_tools(ALL_TOOLS)


__all__ = ["build_llm", "StubChatModel"]
