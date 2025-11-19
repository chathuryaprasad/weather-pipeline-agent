import pytest
from fastapi.testclient import TestClient

from api.main import app
from config.settings import settings


@pytest.fixture(autouse=True)
def configure_token(monkeypatch):
    monkeypatch.setattr(settings, "API_AUTH_TOKEN", "test-token")
    yield


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers():
    return {"Authorization": "Bearer test-token"}


def test_health_requires_token(client):
    response = client.get("/health")
    assert response.status_code == 401


def test_health_success(client):
    response = client.get("/health", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_latest_weather_uses_store(monkeypatch, client):
    monkeypatch.setattr("api.main.get_latest_weather", lambda city: {"city": city, "temperature": 30})
    resp = client.get("/api/weather/latest", params={"city": "Colombo"}, headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["city"] == "Colombo"
    assert body["data"]["temperature"] == 30


def test_history_weather_missing(monkeypatch, client):
    monkeypatch.setattr("api.main.get_weather_history", lambda city, days: [])
    resp = client.get(
        "/api/weather/history",
        params={"city": "Colombo", "days": 5},
        headers=auth_headers(),
    )
    assert resp.status_code == 404


def test_agent_query(monkeypatch, client):
    class FakeAgent:
        def query(self, q):
            return "Sunny"

    monkeypatch.setattr("api.main.get_weather_agent", lambda: FakeAgent())
    resp = client.post(
        "/api/agent/query",
        json={"query": "What is the weather?"},
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["response"] == "Sunny"

