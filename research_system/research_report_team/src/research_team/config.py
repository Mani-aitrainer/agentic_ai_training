"""Central configuration.

Model name, round limits, and the sentinel words the agents use to signal
state (APPROVE / REVISE) all live here so the team's behaviour is tunable in
one place.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # --- LLM ---
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    temperature: float = 0.2

    # --- Conversation control ---
    # The critic says this when the report is good enough -> conversation ends.
    approve_word: str = "APPROVE"
    # The critic says this when the draft needs another pass.
    revise_word: str = "REVISE"
    # Hard ceiling on turns so a stubborn critic can never loop forever.
    max_messages: int = 12
    # How many full research->write->critique rounds we allow.
    max_rounds: int = 3


settings = Settings()
