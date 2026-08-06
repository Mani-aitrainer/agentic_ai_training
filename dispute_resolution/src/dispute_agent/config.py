"""Central configuration for the dispute resolution agent.

Keeping thresholds and model names in one place makes the policy auditable
and the whole system easy to tune without touching business logic.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Repo root -> .../dispute_resolution
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PACKAGE_ROOT / "data"

load_dotenv(PACKAGE_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    # --- LLM ---
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    llm_temperature: float = 0.0

    # --- Policy thresholds ---
    # Refunds at or above this value need a human officer to approve.
    human_approval_threshold: float = 25000.0
    # Fraud score (0-1) at or above this is treated as likely fraud.
    fraud_score_threshold: float = 0.6
    # A duplicate transaction is auto-resolved without human review if below this.
    duplicate_auto_resolve_max: float = 25000.0

    # --- Reliability ---
    # How many times to retry the (flaky) fraud-scoring service before escalating.
    max_fraud_check_attempts: int = 3

    # --- Multi-agent supervisor ---
    # Below this triage confidence, the supervisor loops back for another pass...
    triage_confidence_threshold: float = 0.55
    # ...but never more than this many times.
    max_triage_attempts: int = 2

    data_dir: Path = DATA_DIR


settings = Settings()
