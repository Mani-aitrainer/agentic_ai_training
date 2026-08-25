# =============================================================================
# The "ticket-feeder" - a deliberately tiny SECOND image.
#
# Its only job is to prove container-to-container communication: it talks to
# http://agent:8000 using the SERVICE NAME as a hostname. It never touches
# localhost, and it never uses the published 8000 port on your laptop.
#
# Notice how different this Dockerfile is from app/Dockerfile: no venv, no
# multi-stage build, no compiled dependencies. It uses only the Python standard
# library, so the simplest possible Dockerfile is the correct one. Match the
# Dockerfile to the app - do not cargo-cult a 40-line build for a 40-line app.
# =============================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# Same non-root hygiene as the agent image.
RUN useradd --create-home --uid 10002 feeder
WORKDIR /app
COPY --chown=feeder:feeder feed.py .
USER feeder

# AGENT_URL is injected by Compose. Defaulting it here means `docker run` also
# works if you pass --network and nothing else.
ENV AGENT_URL=http://agent:8000

CMD ["python", "feed.py"]
