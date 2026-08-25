"""FastAPI surface for the agent.

Three endpoints matter for containers:

  /healthz  liveness  - "is the process wedged?"  This is what the Dockerfile
                        HEALTHCHECK and the Compose healthcheck call.
  /readyz   readiness - "can I serve traffic yet?" Returns 503 until startup
                        finished, so `depends_on` and load balancers can wait.
  /chat     the actual work.

Keeping liveness dumb (never call the LLM from it) is deliberate: if OpenAI has
an outage you do NOT want Docker restarting a perfectly healthy container.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from . import __version__
from .config import get_settings
from .graph import build_graph, run_agent
from .logging_config import configure_logging
from .schemas import ChatRequest, ChatResponse, HealthResponse
from .state_store import build_store

log = logging.getLogger(__name__)
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("starting %s v%s env=%s", settings.app_name, __version__, settings.environment)
    _state["graph"] = build_graph(settings)          # compile once per container
    _state["store"] = build_store(settings.redis_url)
    _state["ready"] = True
    yield
    _state["ready"] = False                          # flip false on SIGTERM so a
    log.info("shutting down")                        # proxy stops sending traffic


app = FastAPI(
    title="Support Triage Agent",
    version=__version__,
    description="A minimal LangGraph agent packaged for Docker and Docker Compose.",
    lifespan=lifespan,
)


@app.get("/healthz", response_model=HealthResponse, tags=["ops"])
def healthz() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.environment,
        llm="openai" if settings.llm_enabled else "stub",
    )


@app.get("/readyz", tags=["ops"])
def readyz() -> PlainTextResponse:
    if not _state.get("ready"):
        raise HTTPException(status_code=503, detail="not ready")
    return PlainTextResponse("ready")


@app.get("/metrics", response_class=PlainTextResponse, tags=["ops"])
def metrics() -> str:
    store = _state.get("store")
    served = store.count() if store else 0
    return (
        "# HELP agent_requests_total Chat requests served.\n"
        "# TYPE agent_requests_total counter\n"
        f"agent_requests_total {served}\n"
    )


@app.post("/chat", response_model=ChatResponse, tags=["agent"])
def chat(request: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    count = _state["store"].increment()
    try:
        result = run_agent(request.message, graph=_state["graph"])
    except Exception as exc:  # noqa: BLE001
        log.exception("agent failed")
        raise HTTPException(status_code=502, detail=f"agent error: {exc}") from exc

    log.info(
        "chat handled",
        extra={"extra_fields": {
            "ms": round((time.perf_counter() - started) * 1000, 1),
            "request_no": count,
            "priority": result["priority"],
        }},
    )
    return ChatResponse(session_id=request.session_id, **result)
