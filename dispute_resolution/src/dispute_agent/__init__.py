"""Dispute & Chargeback Resolution Agent (LangGraph, multi-agent)."""
from __future__ import annotations

from .dependencies import (
    Dependencies,
    build_default_dependencies,
    build_offline_dependencies,
)
from .graph import build_graph, build_linear_graph
from .state import DisputeState

__all__ = [
    "build_graph",
    "build_linear_graph",
    "Dependencies",
    "build_default_dependencies",
    "build_offline_dependencies",
    "DisputeState",
]
__version__ = "2.0.0"
