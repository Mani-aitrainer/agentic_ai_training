"""Request / response contracts for the HTTP API."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, examples=["I was charged twice, please refund"])
    session_id: str | None = Field(default=None, examples=["demo-session-1"])


class ChatResponse(BaseModel):
    reply: str
    priority: str
    tools_used: list[str]
    session_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    llm: str
