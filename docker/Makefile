# =============================================================================
# Convenience targets for the Docker sessions. Run from the docker/ folder.
#   Windows: use Git Bash / WSL, or just copy the command out of each recipe.
#   `make help` lists everything.
# =============================================================================
IMAGE ?= langgraph-agent
TAG   ?= 1.0.0

.PHONY: help local-run local-test build run run-env shell inspect logs \
        up up-dev demo scale test size clean nuke

help:            ## list the targets
	@grep -E "^[a-z-]+:.*?## " $(MAKEFILE_LIST) | sed "s/:.*## /\t/"

# ---------------------------- 15: local first --------------------------------
local-run:       ## run the agent on the HOST, no Docker (prove the code works)
	cd app && PYTHONPATH=src python -m support_agent.cli "I was charged twice"

local-test:      ## run pytest on the HOST
	cd app && PYTHONPATH=src python -m pytest -q

# ------------------------------ 13: one image ---------------------------------
build:           ## build the agent image
	docker build -t $(IMAGE):$(TAG) ./app

run: build       ## run a single container, published on :8000
	docker run --rm -p 8000:8000 --name agent $(IMAGE):$(TAG)

run-env: build   ## same, but inject app/.env (real OPENAI_API_KEY)
	docker run --rm -p 8000:8000 --env-file app/.env --name agent $(IMAGE):$(TAG)

shell:           ## open a shell INSIDE the running container
	docker exec -it agent /bin/sh

inspect:         ## show the image's layers and final config
	docker image history $(IMAGE):$(TAG)
	docker image inspect $(IMAGE):$(TAG) --format '{{json .Config}}'

logs:            ## follow the container's stdout
	docker logs -f agent

size:            ## how big did the multi-stage build get?
	docker images $(IMAGE) --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# ---------------------------- 14: many services -------------------------------
up:              ## agent + redis
	docker compose up --build

up-dev:          ## agent + redis with bind-mounted source and --reload
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

demo:            ## also run the feeder (container-to-container communication)
	docker compose --profile demo up --build

scale:           ## three agent replicas on :8000-8002 sharing one Redis counter
	docker compose -f docker-compose.yml -f docker-compose.scale.yml up --build --scale agent=3

# -------------------------- 15: test the IMAGE --------------------------------
# MSYS_NO_PATHCONV=1 stops Git Bash on Windows rewriting /src into
# C:/Program Files/Git/src. It is harmless on Linux and macOS.
test:            ## run the test suite INSIDE the image
	MSYS_NO_PATHCONV=1 docker run --rm --user root -v "$(CURDIR)/app:/src" -w /src -e PYTHONPATH=/src/src \
	  $(IMAGE):$(TAG) sh -c "pip install -q pytest httpx && pytest -q"

# --------------------------------- cleanup ------------------------------------
clean:           ## stop compose, keep images
	-docker compose --profile demo down -v

nuke: clean      ## also delete the images
	-docker rmi $(IMAGE):$(TAG) langgraph-feeder:$(TAG)
