# Docker + LangGraph — Support Triage Agent

The teaching codebase for sessions **13 (Containerization)**, **14 (Compose &
multi-service)** and **15 (Testing dockerized LangGraph)**.

> **Full walkthrough: [`docs/docker-langgraph-guide.html`](docs/docker-langgraph-guide.html)** — open it in a browser.

## What is in here

```
docker/
├─ app/                        the LangGraph agent (the thing we containerise)
│  ├─ Dockerfile               multi-stage build, non-root, healthcheck
│  ├─ .dockerignore            keeps secrets and caches out of the build context
│  ├─ .env.example             copy to .env for real API keys
│  ├─ requirements.txt         pinned runtime deps
│  ├─ requirements-dev.txt     + pytest, httpx, ruff
│  ├─ src/support_agent/
│  │  ├─ graph.py              the LangGraph: agent -> tools -> finalise
│  │  ├─ tools.py              knowledge base + priority classifier
│  │  ├─ llm.py                OpenAI, with an offline stub fallback
│  │  ├─ api.py                FastAPI: /healthz /readyz /metrics /chat
│  │  ├─ state_store.py        Redis or in-memory (the shared-state demo)
│  │  ├─ logging_config.py     JSON logs to stdout
│  │  ├─ config.py             env-driven settings
│  │  └─ cli.py                run the agent without any HTTP
│  └─ tests/                   6 tests, all pass without an API key
├─ client/                     a SECOND image: the container-to-container demo
│  ├─ Dockerfile               deliberately tiny, for contrast
│  └─ feed.py                  calls http://agent:8000 by service name
├─ docker-compose.yml          agent + redis (+ feeder behind a profile)
├─ docker-compose.dev.yml      overlay: bind mount + --reload + DEBUG
├─ docker-compose.scale.yml    overlay: port range, for --scale agent=3
├─ Makefile                    every command in the guide, as a target
└─ docs/docker-langgraph-guide.html
```

## Sixty-second start

```bash
cd docker
docker compose up --build          # agent on http://localhost:8000/docs
curl localhost:8000/healthz
curl -X POST localhost:8000/chat -H 'content-type: application/json' \
     -d '{"message":"I was charged twice, I need a refund"}'
docker compose down -v
```

No `OPENAI_API_KEY` is required — the agent falls back to a deterministic stub
LLM so every learner gets a working container. To use a real key:

```bash
cp app/.env.example app/.env      # then edit OPENAI_API_KEY
docker compose up --build
```

## The three demos

| Command | Shows |
|---|---|
| `make run` / `docker build` + `docker run` | Session 13 — one image, one container |
| `make up` / `docker compose up` | Session 14 — two services on one network |
| `make demo` / `docker compose --profile demo up` | Session 15 — container-to-container calls |
| `make up-dev` | Session 15 — bind mount, live reload, DEBUG logs |
| `make scale` | Session 14 — 3 replicas sharing one Redis counter |
| `make test` | Session 15 — the test suite run *inside* the image |

`make help` lists every target.

## Requirements

Docker Engine 20.10+ and Compose **v2.24+** (the `!override` and
`env_file: required:` syntax needs it). Check with `docker compose version`.
