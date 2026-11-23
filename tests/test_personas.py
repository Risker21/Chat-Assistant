"""Tests for built-in and custom personas."""

from __future__ import annotations


def test_personas_crud_and_builtin_protection(client):
    headers = {"X-Guest-ID": "guest_persona_1"}

    listing = client.get("/api/v1/personas", headers=headers)
    assert listing.status_code == 200
    personas = listing.json()["personas"]
    assert len(personas) >= 5
    assert any(p["id"] == "deepseek" and p["is_builtin"] for p in personas)

    # Cannot edit or delete built-in persona
    assert client.put("/api/v1/personas/deepseek", json={"name": "Fake"}, headers=headers).status_code == 400
    assert client.delete("/api/v1/personas/deepseek", headers=headers).status_code == 400

    # Create custom persona
    created = client.post(
        "/api/v1/personas",
        json={
            "name": "老王",
            "title": "架构师",
            "description": "擅长高并发架构设计",
            "system_prompt": "你是一位资深系统架构师。",
            "default_model": "deepseek",
            "icon": "fa-code",
        },
        headers=headers,
    )
    assert created.status_code == 201
    pid = created.json()["id"]
    assert created.json()["is_builtin"] is False

    # Update custom persona
    updated = client.put(
        f"/api/v1/personas/{pid}",
        json={"title": "首席架构师"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "首席架构师"

    # Another guest cannot delete it
    other_headers = {"X-Guest-ID": "guest_persona_2"}
    assert client.delete(f"/api/v1/personas/{pid}", headers=other_headers).status_code == 404

    # Owner deletes it
    assert client.delete(f"/api/v1/personas/{pid}", headers=headers).status_code == 204
