from fastapi.testclient import TestClient

from support_agent.api import app


def test_health_and_chat():
    with TestClient(app) as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        assert client.get("/readyz").status_code == 200

        reply = client.post("/chat", json={"message": "I need a refund", "session_id": "t1"})
        assert reply.status_code == 200
        body = reply.json()
        assert body["session_id"] == "t1"
        assert body["priority"] in {"P1", "P2", "P3"}

        assert "agent_requests_total" in client.get("/metrics").text


def test_validation_rejects_empty_message():
    with TestClient(app) as client:
        assert client.post("/chat", json={"message": ""}).status_code == 422
