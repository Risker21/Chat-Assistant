"""Tests for conversation CRUD, search, ownership isolation, and export."""

from __future__ import annotations


def test_conversation_lifecycle_and_isolation(client):
    h1 = {"X-Guest-ID": "guest_owner_one"}
    h2 = {"X-Guest-ID": "guest_owner_two"}

    c1 = client.post(
        "/api/v1/conversations",
        json={"title": "Python 架构讨论", "model": "deepseek", "persona_id": "deepseek"},
        headers=h1,
    )
    assert c1.status_code == 201
    conv_id = c1.json()["id"]

    # Another guest cannot read, patch, or delete c1
    assert client.get(f"/api/v1/conversations/{conv_id}", headers=h2).status_code == 404
    assert client.patch(f"/api/v1/conversations/{conv_id}", json={"title": "hacked"}, headers=h2).status_code == 404
    assert client.delete(f"/api/v1/conversations/{conv_id}", headers=h2).status_code == 404

    # Rename & pin
    patched = client.patch(
        f"/api/v1/conversations/{conv_id}",
        json={"title": "FastAPI 生产实践", "pinned": True, "temperature": 0.3},
        headers=h1,
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "FastAPI 生产实践"
    assert patched.json()["pinned"] is True
    assert patched.json()["temperature"] == 0.3

    # Search
    search_hit = client.get("/api/v1/conversations?q=FastAPI", headers=h1).json()
    assert search_hit["total"] == 1
    search_miss = client.get("/api/v1/conversations?q=RustLang", headers=h1).json()
    assert search_miss["total"] == 0

    # Export Markdown and JSON
    md = client.get(f"/api/v1/conversations/{conv_id}/export?format=markdown", headers=h1)
    assert md.status_code == 200
    assert "# FastAPI 生产实践" in md.text

    js = client.get(f"/api/v1/conversations/{conv_id}/export?format=json", headers=h1)
    assert js.status_code == 200
    assert js.json()["title"] == "FastAPI 生产实践"

    # Delete
    assert client.delete(f"/api/v1/conversations/{conv_id}", headers=h1).status_code == 204
    assert client.get(f"/api/v1/conversations/{conv_id}", headers=h1).status_code == 404
