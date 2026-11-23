"""Tests for guest identity, JWT registration/login, and guest data migration."""

from __future__ import annotations


def test_guest_identity_me(client):
    resp = client.get("/api/v1/auth/me", headers={"X-Guest-ID": "guest_alpha_1234"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_guest"] is True
    assert body["id"] == "guest_alpha_1234"


def test_register_login_and_guest_migration(client):
    guest_headers = {"X-Guest-ID": "guest_migrate_9999"}

    # Create a conversation and custom persona as a guest
    conv = client.post(
        "/api/v1/conversations",
        json={"title": "游客创建的对话", "model": "deepseek", "persona_id": "deepseek"},
        headers=guest_headers,
    )
    assert conv.status_code == 201
    conv_id = conv.json()["id"]

    persona = client.post(
        "/api/v1/personas",
        json={
            "name": "测试角色",
            "title": "测试专家",
            "system_prompt": "你是一个测试专家",
        },
        headers=guest_headers,
    )
    assert persona.status_code == 201

    # Register with the same X-Guest-ID -> data should migrate automatically
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice_dev",
            "password": "password123",
            "display_name": "Alice",
            "email": "alice@example.com",
        },
        headers=guest_headers,
    )
    assert reg.status_code == 201
    reg_data = reg.json()
    assert reg_data["migrated_conversations"] == 1
    assert reg_data["migrated_personas"] == 1
    token = reg_data["access_token"]

    # Duplicate username rejected
    dup = client.post(
        "/api/v1/auth/register",
        json={"username": "alice_dev", "password": "password123"},
    )
    assert dup.status_code == 409

    # Authenticated /me returns user profile
    auth_headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["is_guest"] is False
    assert me.json()["username"] == "alice_dev"

    # Migrated conversation is owned by Alice and no longer by the old guest
    alice_convs = client.get("/api/v1/conversations", headers=auth_headers).json()["conversations"]
    assert any(c["id"] == conv_id for c in alice_convs)

    guest_convs = client.get("/api/v1/conversations", headers=guest_headers).json()["conversations"]
    assert guest_convs == []

    # Login works with username and rejects bad password
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"username": "alice_dev", "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401

    good_login = client.post(
        "/api/v1/auth/login",
        json={"username": "alice_dev", "password": "password123"},
    )
    assert good_login.status_code == 200
    assert good_login.json()["user"]["username"] == "alice_dev"
