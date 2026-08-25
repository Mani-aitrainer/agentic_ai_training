"""Tools the agent may call.

Deliberately dependency-free and deterministic so the workshop demo behaves the
same on every machine and inside every container.
"""

from langchain_core.tools import tool

_KB: dict[str, str] = {
    "refund": "Refunds are processed within 5-7 business days to the original payment method.",
    "password": "Ask the customer to use the 'Forgot password' link; reset links expire in 30 minutes.",
    "shipping": "Standard shipping is 3-5 days; express is next business day before 6pm cut-off.",
    "invoice": "Invoices are emailed on the 1st of each month and are downloadable from Billing > History.",
}

_PRIORITY_RULES: dict[str, tuple[str, ...]] = {
    "P1": ("outage", "cannot login", "data loss", "charged twice", "security"),
    "P2": ("refund", "invoice", "billing", "error"),
    "P3": ("how do i", "question", "shipping", "password"),
}


@tool
def search_knowledge_base(query: str) -> str:
    """Look up an answer for a customer question in the internal knowledge base."""
    q = query.lower()
    hits = [text for key, text in _KB.items() if key in q]
    if not hits:
        return "NO_MATCH: nothing in the knowledge base covers this question."
    return " ".join(hits)


@tool
def classify_priority(ticket_text: str) -> str:
    """Return the support priority (P1, P2 or P3) for a ticket."""
    text = ticket_text.lower()
    for priority, keywords in _PRIORITY_RULES.items():
        if any(keyword in text for keyword in keywords):
            return priority
    return "P3"


ALL_TOOLS = [search_knowledge_base, classify_priority]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
