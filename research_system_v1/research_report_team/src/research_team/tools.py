"""Tools the Researcher agent can call.

This is the "tool integration in AutoGen" concept. In AutoGen v0.4 a tool is
just a typed Python function passed to an agent via ``tools=[...]``; the agent's
model decides when to call it. The function's name, signature, and docstring are
what the model sees -- so the docstring is effectively part of the prompt.

We provide a real DuckDuckGo-backed search and an offline stub. The team is
wired with whichever is appropriate for the run mode.
"""
from __future__ import annotations


def web_search(query: str) -> str:
    """Search the web for up-to-date information on a query and return a short
    digest of the top results. Use this to gather facts before writing."""
    try:
        # Lazy import so offline runs never need the dependency installed.
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # older package name
        except ImportError:
            return ("web_search unavailable: install 'ddgs' to enable live search. "
                    "Proceeding without external sources.")

    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=5))
    except Exception as exc:  # network issues, rate limits, etc.
        return f"web_search error: {exc}. Proceeding without external sources."

    if not hits:
        return f"No results found for '{query}'."
    lines = [f"- {h.get('title', '')}: {h.get('body', '')[:160]}" for h in hits]
    return f"Top results for '{query}':\n" + "\n".join(lines)


def stub_web_search(query: str) -> str:
    """Offline stand-in for web_search: returns deterministic canned context so
    the team runs with no network. Same signature as the real tool."""
    return (
        f"[offline results for '{query}']\n"
        "- LangGraph: a stateful graph runtime for controllable agent workflows.\n"
        "- AutoGen: a conversational multi-agent framework (v0.4, async).\n"
        "- Common practice in 2026: use LangGraph for control, AutoGen for dialogue."
    )
