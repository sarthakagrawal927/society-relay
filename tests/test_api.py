import pytest
from fastapi.testclient import TestClient

from relay import app as module
from relay.store import Store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "store", Store(tmp_path / "test.db"))
    return TestClient(module.app)


def test_session_is_required(client):
    assert client.get("/api/state").status_code == 401


def test_idempotent_report_retry(client):
    client.post("/api/session")
    body = {"text": "Water supply has stopped in Tower A.", "unit": "A-304", "request_id": "request-001"}
    a = client.post("/api/reports", json=body)
    b = client.post("/api/reports", json=body)
    assert a.json()["id"] == b.json()["id"]
    assert len(client.get("/api/state").json()["incidents"]) == 1


def test_cross_origin_mutation_rejected(client):
    assert client.post("/api/session", headers={"Origin": "https://attacker.example"}).status_code == 403


def test_client_cannot_supply_quote(client):
    client.post("/api/session")
    assert client.post("/api/scenario").status_code == 200
    s = client.get("/api/state").json()
    r = client.post(
        f"/api/incidents/{s['incidents'][0]['id']}/action",
        json={"action": "approve", "role": "committee", "quote": 1, "proposal_id": "fake"},
    )
    assert r.status_code == 409


def test_static_product_loads(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]
