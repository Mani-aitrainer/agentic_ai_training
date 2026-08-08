"""A scripted tool-calling chat model for offline runs and tests.

The real Fraud Investigator uses OpenAI, which decides tool calls dynamically.
To exercise the *same* graph wiring offline (no API key), we provide a model
that supports ``bind_tools`` and emits a scripted sequence of AIMessages --
some carrying tool calls, ending in a plain verdict. The ToolNode + conditional
loop in the graph then behaves exactly as it would with a live model.
"""
from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedToolModel(BaseChatModel):
    """Returns pre-scripted AIMessages in order. Supports bind_tools (no-op)."""

    def __init__(self, responses: list[AIMessage], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        object.__setattr__(self, "_responses", list(responses))
        object.__setattr__(self, "_i", 0)

    @property
    def _llm_type(self) -> str:  # pragma: no cover - trivial
        return "scripted-tool-model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedToolModel":
        # Scripted, so tools are accepted and ignored.
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        i = object.__getattribute__(self, "_i")
        responses = object.__getattribute__(self, "_responses")
        # Clamp to the last message so extra loops don't crash.
        resp = responses[min(i, len(responses) - 1)]
        object.__setattr__(self, "_i", i + 1)
        return ChatResult(generations=[ChatGeneration(message=resp)])


def scripted_investigator(txn_id: str) -> ScriptedToolModel:
    """A deterministic 'investigation': call compute_fraud_signals, then verdict."""
    return ScriptedToolModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "compute_fraud_signals",
                        "args": {"txn_id": txn_id},
                        "id": "call_signals",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content=(
                    "Investigation complete. I computed the fraud signals for this "
                    "transaction; see the score in the tool result. Verdict follows "
                    "from whether that score crosses the bank threshold."
                )
            ),
        ]
    )
