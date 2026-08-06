"""Dependency container.

The graph's agents/nodes need a data repository, a classifier (triage LLM
boundary), a fraud service (for the legacy linear graph), and a customer
message writer (resolution LLM boundary). Bundling them here and injecting the
bundle is what keeps every component unit-testable: tests pass stubs,
production passes the real OpenAI-backed implementations.
"""
from __future__ import annotations

from dataclasses import dataclass

from .agents.specialists import MessageWriter, OpenAIMessageWriter, StubMessageWriter
from .classifier import Classifier, OpenAIClassifier
from .config import settings
from .data_access import JsonRepository
from .fraud import FraudService


@dataclass
class Dependencies:
    repo: JsonRepository
    classifier: Classifier
    fraud_service: FraudService
    message_writer: MessageWriter


def build_default_dependencies() -> Dependencies:
    """Wire up the real, production dependencies (needs OPENAI_API_KEY at call time)."""
    return Dependencies(
        repo=JsonRepository(),
        classifier=OpenAIClassifier(
            model=settings.openai_model,
            temperature=settings.llm_temperature,
        ),
        fraud_service=FraudService(),
        message_writer=OpenAIMessageWriter(model=settings.openai_model),
    )


def build_offline_dependencies(fraud_fails: int = 0) -> Dependencies:
    """All-stub dependencies -- runs with no API key. Used by --offline and tests."""
    from .classifier import StubClassifier

    return Dependencies(
        repo=JsonRepository(),
        classifier=StubClassifier(),
        fraud_service=FraudService(fail_times=fraud_fails),
        message_writer=StubMessageWriter(),
    )
