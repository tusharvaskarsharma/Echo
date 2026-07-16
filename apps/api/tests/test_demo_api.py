from fastapi.testclient import TestClient
from app.main import app


def test_portugal_is_answered_with_sources():
    with TestClient(app) as client:
        response = client.post("/echo/eleanor-74/converse", json={"question": "Did you ever travel to Portugal?"})
        assert response.status_code == 200
        assert "event: sources" in response.text
        assert "Portugal" in response.text


def test_unknown_topic_refuses():
    with TestClient(app) as client:
        response = client.post("/echo/eleanor-74/converse", json={"question": "What did you think of my husband?"})
        assert "event: refusal" in response.text


def test_private_memory_cannot_be_retrieved():
    with TestClient(app) as client:
        for memory_id in ("memory-01", "memory-02", "memory-03"):
            response = client.patch(f"/memories/{memory_id}", json={"consent_level": "private"})
            assert response.status_code == 200
        response = client.post("/echo/eleanor-74/converse", json={"question": "Did you ever travel to Portugal?"})
        assert "event: refusal" in response.text
