from fastapi.testclient import TestClient

from analysis.main import app


def test_analyze_endpoint():
    client = TestClient(app)
    r = client.post(
        "/analyze",
        json={
            "run_id": "1",
            "log_text": "ModuleNotFoundError: pydantic",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["run_id"] == "1"
    assert "remediation" in data


def test_cluster_endpoint():
    client = TestClient(app)
    r = client.post("/cluster", json=["error a", "error a similar", "different xyz"])
    assert r.status_code == 200
    body = r.json()
    assert "labels" in body and len(body["labels"]) == 3
