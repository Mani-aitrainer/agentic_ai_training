"""LangChain tools exposed to tool-calling agents inside the graph.

This is the "using LangChain tools inside LangGraph" concept. The Fraud
Investigator Agent is given these as real ``@tool`` functions; the model
decides which to call and with what arguments, and a LangGraph ``ToolNode``
executes them.

Because tools must be plain callables the model can invoke, they read their
data from a module-level repository set via ``bind_repository(...)``. The
graph builder calls that once at assembly time. (Deterministic nodes elsewhere
still use the injected repository directly -- tools are only for the
model-driven agent.)
"""
from __future__ import annotations

from langchain_core.tools import tool

from .data_access import JsonRepository, RecordNotFound
from .fraud import score_fraud

# Module-level repository the tools read from. Set by bind_repository().
_repo: JsonRepository | None = None


def bind_repository(repo: JsonRepository) -> None:
    """Point the tool functions at a repository (call once when building the graph)."""
    global _repo
    _repo = repo


def _require_repo() -> JsonRepository:
    if _repo is None:
        raise RuntimeError("tools repository not bound; call bind_repository() first")
    return _repo


@tool
def lookup_transaction(txn_id: str) -> dict:
    """Fetch the full details of a card/UPI transaction by its transaction id.
    Use this to inspect amount, channel, country, card_present and duplicate links."""
    try:
        return _require_repo().get_transaction(txn_id)
    except RecordNotFound:
        return {"error": f"transaction {txn_id} not found"}


@tool
def lookup_merchant(merchant_id: str) -> dict:
    """Fetch a merchant's profile: category, risk_rating, chargeback_rate, country.
    Use this to judge whether the merchant is high risk."""
    try:
        return _require_repo().get_merchant(merchant_id)
    except RecordNotFound:
        return {"error": f"merchant {merchant_id} not found"}


@tool
def lookup_customer_history(customer_id: str) -> dict:
    """Fetch a customer's account age and prior dispute / confirmed-fraud counts.
    Use this to see whether the customer is new or has a history of fraud."""
    try:
        c = _require_repo().get_customer(customer_id)
    except RecordNotFound:
        return {"error": f"customer {customer_id} not found"}
    return {
        "customer_id": c.get("customer_id"),
        "account_age_months": c.get("account_age_months"),
        "prior_disputes": c.get("prior_disputes"),
        "prior_fraud_confirmed": c.get("prior_fraud_confirmed"),
    }


@tool
def compute_fraud_signals(txn_id: str) -> dict:
    """Compute a fraud score (0-1) and the list of triggered risk signals for a
    transaction. Use this once you have gathered the relevant context."""
    repo = _require_repo()
    try:
        txn = repo.get_transaction(txn_id)
        customer = repo.get_customer(txn["customer_id"])
        merchant = repo.get_merchant(txn["merchant_id"])
    except RecordNotFound as exc:
        return {"error": str(exc)}
    res = score_fraud(txn, customer, merchant)
    return {"fraud_score": res.score, "signals": res.signals}


# The toolset handed to the Fraud Investigator Agent.
FRAUD_INVESTIGATION_TOOLS = [
    lookup_transaction,
    lookup_merchant,
    lookup_customer_history,
    compute_fraud_signals,
]
