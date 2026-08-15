"""Running the team and shaping its output.

AutoGen is async, so we centralise the ``await team.run(...)`` call here and
convert the raw message list into a tidy ``ReportResult``. Keeping this
separate from team *assembly* means the graph layer (Section 9) can call one
clean function.
"""
from __future__ import annotations

from autogen_agentchat.base import TaskResult

from .config import settings
from .team import ReportResult


def _to_text(content) -> str:
    """AutoGen message content may be a string or a list of parts; normalise it."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(c) for c in content)
    return str(content)


def summarise(result: TaskResult) -> ReportResult:
    """Turn AutoGen's TaskResult into our ReportResult.

    The final report is the Writer's last message; approval is whether the
    Critic's APPROVE word triggered termination.
    """
    transcript: list[tuple[str, str]] = []
    last_writer_msg = ""
    for msg in result.messages:
        source = getattr(msg, "source", "?")
        text = _to_text(getattr(msg, "content", ""))
        transcript.append((source, text))
        if source == "writer":
            last_writer_msg = text

    approved = settings.approve_word in (result.stop_reason or "")
    # rounds = number of times the critic spoke
    rounds = sum(1 for s, _ in transcript if s == "critic")

    return ReportResult(
        report=last_writer_msg,
        approved=approved,
        rounds=rounds,
        stop_reason=result.stop_reason or "",
        transcript=transcript,
    )


async def run_team(team, topic: str) -> ReportResult:
    """Run a team on a topic and return a structured result."""
    task = f"Write a well-structured report on: {topic}"
    result = await team.run(task=task)
    return summarise(result)
