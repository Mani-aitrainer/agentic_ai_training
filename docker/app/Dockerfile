# syntax=docker/dockerfile:1.7
# =============================================================================
# Multi-stage build for the LangGraph Support Triage Agent.
#
#   Stage 1 (builder)  - has compilers and pip; produces a self-contained venv.
#   Stage 2 (runtime)  - copies ONLY that venv + the source. No compilers, no
#                        pip cache, no build tools => smaller and less to patch.
#
# Line-by-line explanation: ../docs/docker-langgraph-guide.html
# =============================================================================

# ------------------------------ stage 1: build -------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Copy ONLY the requirements first. Docker caches each layer; as long as this
# file is unchanged the (slow) pip install layer is reused even when your
# application code changes. Copying the whole app first would break that.
COPY requirements.txt .

RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

# ----------------------------- stage 2: runtime ------------------------------
FROM python:3.12-slim AS runtime

# PYTHONUNBUFFERED is mandatory in containers: without it Python buffers stdout
# and `docker logs` shows nothing until the buffer flushes (or never, on crash).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PORT=8000   

# Run as a non-root user. If the process is compromised, the attacker lands as
# uid 10001 with no write access to the filesystem instead of as root.
RUN groupadd --gid 10001 appuser \
 && useradd --uid 10001 --gid appuser --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser src/ /app/src/

USER appuser

EXPOSE 8000

# Docker-level health check. It makes `docker ps` print healthy/unhealthy and
# it is what Compose's `depends_on: condition: service_healthy` waits on.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status==200 else 1)"

# exec form (JSON array), NOT shell form. With exec form uvicorn is PID 1 and
# receives SIGTERM directly, so `docker stop` shuts down gracefully. Shell form
# would put /bin/sh at PID 1 and swallow the signal -> Docker waits the full 10s
# grace period and then SIGKILLs the container on every restart.
CMD ["uvicorn", "support_agent.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
