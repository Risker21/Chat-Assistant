"""Tests for health checks, model catalog, frontend page, and middleware."""

from __future__ import annotations


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert "version" in data
    assert "X-Request-ID" in resp.headers
    assert "X-Process-Time-Ms" in resp.headers


def test_models_v1_and_legacy(client):
    resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    model_values = {m["value"] for m in data["models"]}
    assert {"deepseek", "qwen", "hunyuan", "glm", "doubao"}.issubset(model_values)

    legacy = client.get("/models")
    assert legacy.status_code == 200
    assert len(legacy.json()["models"]) == len(data["models"])


def test_index_page_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "解忧小铺" in resp.text


def test_rate_limiter_enforces_limit(client):
    limiter = client.app.state.rate_limiter
    limiter.max_requests = 3
    limiter.reset()

    headers = {"X-Guest-ID": "ratelimit_guest_1"}
    for _ in range(3):
        assert client.get("/api/v1/models", headers=headers).status_code == 200

    blocked = client.get("/api/v1/models", headers=headers)
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in blocked.headers
