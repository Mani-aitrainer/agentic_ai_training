"""FastAPI app that exposes the LangGraph agent.

Run:  uvicorn main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent import agent

app = FastAPI(title="Simple Support Agent")

INDEX_HTML = Path(__file__).parent / "index.html"


class TicketRequest(BaseModel):
    message: str


class TicketResponse(BaseModel):
    message: str
    category: str
    reply: str
    gemini_reply: str
    claude_reply: str


@app.get("/")
def home():
    return FileResponse(INDEX_HTML)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ticket", response_model=TicketResponse)
def handle_ticket(req: TicketRequest):
    result = agent.invoke({"message": req.message})
    return TicketResponse(**result)
