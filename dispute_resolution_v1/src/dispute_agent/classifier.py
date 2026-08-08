"""The LLM boundary of the system.

We isolate the one place that calls OpenAI behind a small Protocol. Everything
else in the graph depends on the Protocol, not on OpenAI. That gives us two
wins:
  1. The graph can be unit-tested offline by injecting a StubClassifier.
  2. Swapping OpenAI for Bedrock/Azure later touches exactly one class.
"""
from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

# The categories the agent understands. Kept as a constant so tests and prompts
# stay in sync.
CATEGORIES = ("DUPLICATE", "FRAUD", "SERVICE_NOT_RENDERED", "UNRECOGNIZED", "OTHER")

SYSTEM_PROMPT = (
    "You are a payment dispute classifier for an Indian retail bank. "
    "Read the customer's statement and the transaction context, then classify "
    "the dispute into exactly one category:\n"
    "- DUPLICATE: customer says they were charged more than once for one purchase.\n"
    "- FRAUD: customer says they never made the transaction / card was compromised.\n"
    "- SERVICE_NOT_RENDERED: customer made the payment but goods/services never arrived.\n"
    "- UNRECOGNIZED: customer does not recognise the charge but does not clearly allege fraud.\n"
    "- OTHER: anything that does not fit the above.\n"
    "Return the category and a confidence between 0 and 1."
)


class Classification(BaseModel):
    """Structured result returned by the classifier."""

    category: str = Field(description=f"One of: {', '.join(CATEGORIES)}")
    confidence: float = Field(ge=0.0, le=1.0, description="0-1 confidence")
    rationale: str = Field(default="", description="Short reason for the choice")


class Classifier(Protocol):
    """Anything that can turn a dispute into a Classification."""

    def classify(self, customer_statement: str, transaction: dict) -> Classification: ...


class OpenAIClassifier:
    """Production implementation backed by OpenAI structured output."""

    def __init__(self, model: str, temperature: float = 0.0) -> None:
        # Imported lazily so tests that never touch OpenAI don't need the
        # dependency configured (no API key required to import this module).
        from langchain_openai import ChatOpenAI

        self._llm = ChatOpenAI(model=model, temperature=temperature)
        self._structured = self._llm.with_structured_output(Classification)

    def classify(self, customer_statement: str, transaction: dict) -> Classification:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Transaction: {transaction}\n\n"
                    f"Customer statement: {customer_statement}"
                ),
            },
        ]
        result = self._structured.invoke(messages)
        # Guard against a model returning an out-of-vocabulary label.
        if result.category not in CATEGORIES:
            result = result.model_copy(update={"category": "OTHER"})
        return result


class StubClassifier:
    """Deterministic classifier for tests and offline demos.

    Uses simple keyword rules so the full graph can run with no network call.
    """

    def classify(self, customer_statement: str, transaction: dict) -> Classification:
        text = customer_statement.lower()
        if "twice" in text or "duplicate" in text or transaction.get("duplicate_of"):
            return Classification(category="DUPLICATE", confidence=0.95, rationale="stub: duplicate")
        if "never made" in text or "stole" in text or "fraud" in text:
            return Classification(category="FRAUD", confidence=0.9, rationale="stub: fraud")
        if "never arrived" in text or "never delivered" in text or "delivery" in text:
            return Classification(
                category="SERVICE_NOT_RENDERED", confidence=0.85, rationale="stub: SNR"
            )
        if "do not recognise" in text or "don't recognise" in text or "not recognise" in text:
            return Classification(category="UNRECOGNIZED", confidence=0.7, rationale="stub: unrecognized")
        return Classification(category="OTHER", confidence=0.5, rationale="stub: fallthrough")
