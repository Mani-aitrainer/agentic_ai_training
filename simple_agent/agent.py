"""A tiny LangGraph agent: classify a support message, then write replies.

Flow:
                  +-> respond       (template reply) -+
    START -> classify -> gemini_reply  (Google Gemini)  -+-> END
                  +-> claude_reply  (Anthropic Claude) -+

The three reply nodes run in parallel after classify.
LLM nodes need an API key (GEMINI_API_KEY / ANTHROPIC_API_KEY).
Keys are read from the .env file next to this script (see .env.example).
Without a key they return a short note instead of failing.
"""

import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

# Load keys from simple_agent/.env. Real environment variables still win.
load_dotenv(Path(__file__).parent / ".env")

GEMINI_MODEL = "gemini-2.5-flash"
CLAUDE_MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = (
    "You are a friendly customer support agent. "
    "Write a short reply (2-3 sentences) to the customer. "
    "The ticket category is: {category}."
)


class TicketState(TypedDict, total=False):
    message: str       # input from the user
    category: str      # set by the classify node
    reply: str         # set by the respond node
    gemini_reply: str  # set by the gemini_reply node
    claude_reply: str  # set by the claude_reply node


KEYWORDS = {
    "billing": ["refund", "charge", "invoice", "payment", "bill"],
    "technical": ["error", "bug", "crash", "login", "not working"],
}

REPLIES = {
    "billing": "Thanks! Our billing team will check your payment within 24 hours.",
    "technical": "Sorry for the trouble. Our tech team is looking into the issue.",
    "general": "Thanks for reaching out. We will get back to you soon.",
}


def classify(state: TicketState) -> TicketState:
    """Node 1: pick a category by looking for keywords."""
    text = state["message"].lower()
    for category, words in KEYWORDS.items():
        if any(word in text for word in words):
            return {"category": category}
    return {"category": "general"}


def respond(state: TicketState) -> TicketState:
    """Node 2: write a reply based on the category."""
    return {"reply": REPLIES[state["category"]]}


def gemini_reply(state: TicketState) -> TicketState:
    """Node 3: ask Google Gemini to write a reply."""
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        return {"gemini_reply": "(skipped: set GEMINI_API_KEY to call Gemini)"}

    from google import genai
    from google.genai import types

    client = genai.Client()  # reads GEMINI_API_KEY / GOOGLE_API_KEY
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=state["message"],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT.format(category=state["category"]),
            ),
        )
        return {"gemini_reply": response.text or ""}
    except Exception as err:
        return {"gemini_reply": f"(Gemini error: {err})"}


def claude_reply(state: TicketState) -> TicketState:
    """Node 4: ask Anthropic Claude to write a reply."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return {"claude_reply": "(skipped: set ANTHROPIC_API_KEY to call Claude)"}

    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    try:
        response = client.beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT.format(category=state["category"]),
            messages=[{"role": "user", "content": state["message"]}],
            output_config={"effort": "low"},  # short replies, keep it fast
            # If Claude declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIError as err:
        return {"claude_reply": f"(Claude error: {err})"}

    if response.stop_reason == "refusal":
        return {"claude_reply": "(Claude declined to answer this message)"}
    text = "".join(b.text for b in response.content if b.type == "text")
    return {"claude_reply": text}


def build_graph():
    graph = StateGraph(TicketState)
    graph.add_node("classify", classify)
    graph.add_node("respond", respond)
    graph.add_node("gemini_reply", gemini_reply)
    graph.add_node("claude_reply", claude_reply)

    graph.add_edge(START, "classify")
    for node in ("respond", "gemini_reply", "claude_reply"):
        graph.add_edge("classify", node)  # fan out: run in parallel
        graph.add_edge(node, END)
    return graph.compile()


agent = build_graph()


if __name__ == "__main__":
    print(agent.invoke({"message": "I was charged twice, please refund"}))
