"""Error handling and edge-case types for the AutoGen<->LangGraph integration.

Section 9 asks explicitly for "error handling and edge case design". The edge
cases that actually bite when you embed a chatty async agent team inside a
deterministic graph are:

  * the team never approves (hits the message cap)         -> NotApprovedError
  * a model/tool call raises (network, rate limit, bug)    -> TeamRunError
  * the team produces an empty report                      -> EmptyReportError

We model them as explicit exceptions so the graph can route on them instead of
crashing the whole run.
"""
from __future__ import annotations


class TeamError(Exception):
    """Base class for all team-execution problems."""

class TeamRunError(TeamError):
    """The AutoGen team raised while running (network, model, tool, etc.)."""


class NotApprovedError(TeamError):
    """The team stopped without the Critic approving (hit the message cap)."""


class EmptyReportError(TeamError):
    """The team finished but produced no usable report text."""
