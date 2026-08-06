from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from langchain_openai import ChatOpenAI

HUMAN_APPROVAL_AMOUNT_THRESHOLD = 500_000   # more than 5L
HUMAN_APPROVAL_FOIR_THRESHOLD = 30          # more than 30%

import os
os.environ["OPENAI_API_KEY"] = ""

# ---------- 1. PARSED SHAPE : what the LLM must extract from the raw prompt ----------
class ParsedDisbursalRequest(TypedDict):
    """Structured fields extracted from the officer's free-text disbursal request."""
    pan: str
    monthly_income: float
    existing_emi: float
    amount: float


# ---------- 2. STATE : the shared dict every node reads and writes ----------
class State(TypedDict):
    prompt: str              # <-- raw user prompt, e.g. "PAN ABCDE1234F, monthly income 90000, existing EMI 30000. Approve disbursal of 500000?"
    pan: str
    monthly_income: float
    existing_emi: float
    amount: float
    foir: float
    status: str


# ---------- 3. NODES ----------
parser_model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
structured_parser = parser_model.with_structured_output(ParsedDisbursalRequest)

def parse_request(state: State) -> dict:
    """LLM node: turns the free-text prompt into the typed fields the rest of the graph needs."""
    parsed: ParsedDisbursalRequest = structured_parser.invoke(
        "Extract the PAN number, monthly income, existing EMI, and requested "
        f"disbursal amount from this request:\n\n{state['prompt']}"
    )
    print(f"[parse_request] parsed = {parsed}")
    return {
        "pan": parsed["pan"],
        "monthly_income": parsed["monthly_income"],
        "existing_emi": parsed["existing_emi"],
        "amount": parsed["amount"],
    }


def calculate_foir(state: State) -> dict:
    foir = round((state["existing_emi"] / state["monthly_income"]) * 100, 1)
    print(f"[calculate_foir] FOIR = {foir}%")
    return {"foir": foir}


def prepare(state: State) -> dict:
    print(f"[prepare] disbursal of Rs.{state['amount']} for PAN {state['pan']} (FOIR {state['foir']}%)")
    return {"status": "PENDING_APPROVAL"}


def needs_human_approval(state: State) -> Literal["officer_approval", "auto_approve"]:
    """Policy: large amount or high FOIR must be reviewed by a human officer."""
    if state["amount"] > HUMAN_APPROVAL_AMOUNT_THRESHOLD or state["foir"] > HUMAN_APPROVAL_FOIR_THRESHOLD:
        return "officer_approval"
    return "auto_approve"


def officer_approval(state: State) -> dict:
    # execution STOPS here and control returns to the caller
    decision = interrupt({
        "question": "Approve disbursal?",
        "amount": state["amount"],
        "foir": state["foir"],
    })
    return {"status": "APPROVED" if decision == "yes" else "REJECTED"}


def auto_approve(state: State) -> dict:
    print(f"[auto_approve] within policy (amount <= Rs.{HUMAN_APPROVAL_AMOUNT_THRESHOLD}, FOIR <= {HUMAN_APPROVAL_FOIR_THRESHOLD}%) — no officer needed")
    return {"status": "APPROVED"}


def disburse(state: State) -> dict:
    print(f"[disburse] final status = {state['status']}")
    return {}


# ---------- 4. BUILD THE GRAPH ----------
builder = StateGraph(State)
builder.add_node("parse_request", parse_request)
builder.add_node("calculate_foir", calculate_foir)
builder.add_node("prepare", prepare)
builder.add_node("officer_approval", officer_approval)
builder.add_node("auto_approve", auto_approve)
builder.add_node("disburse", disburse)

builder.add_edge(START, "parse_request")
builder.add_edge("parse_request", "calculate_foir")
builder.add_edge("calculate_foir", "prepare")
builder.add_conditional_edges(
    "prepare", needs_human_approval,
    {"officer_approval": "officer_approval", "auto_approve": "auto_approve"},
)
builder.add_edge("officer_approval", "disburse")
builder.add_edge("auto_approve", "disburse")
builder.add_edge("disburse", END)

graph = builder.compile(checkpointer=InMemorySaver())   # HITL REQUIRES a checkpointer

config = {"configurable": {"thread_id": "loan-77"}}

# --- first call: amount 5L and FOIR 33.3% (>30%) -> routes to officer_approval, runs until the interrupt, then returns ---
prompt = "PAN ABCDE1234F, monthly income 90000, existing EMI 30000. Approve disbursal of Rs.500000?"
paused = graph.invoke({"prompt": prompt}, config)
print("PAUSED AT:", paused["__interrupt__"])

# --- the officer decides (minutes or days later, different process, same thread_id) ---
final = graph.invoke(Command(resume=(input())), config)
print("FINAL:", final)