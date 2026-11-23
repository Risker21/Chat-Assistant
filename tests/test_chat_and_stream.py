"""Tests for SSE streaming chat, sync chat, web search citations, regenerate, and edit."""

from __future__ import annotations

import json

from app.services import chat_service
from app.services.model_registry import model_registry
from tests.conftest import FakeStreamingLLM


def _parse_sse(raw_text: str):
    events = []
    for frame in raw_text.strip().split("\n\n"):
        if not frame.strip():
            continue
        ev_name = "message"
        data_str = ""
        for line in frame.splitlines():
            if line.startswith("event:"):
                ev_name = line[6:].strip()
            elif line.startswith("data:"):
                data_str += line[5:].strip()
        events.append((ev_name, json.loads(data_str) if data_str else {}))
    return events


def test_sse_stream_chat_and_persistence(client, monkeypatch):
    fake_llm = FakeStreamingLLM(["你好", "，我是", " Zoe！"])
    monkeypatch.setattr(model_registry, "get_chat_client", lambda model_id, temperature=0.7: fake_llm)

    headers = {"X-Guest-ID": "guest_stream_1"}
    resp = client.post(
        "/api/v1/chat/stream",
        json={"message": "嗨，打个招呼吧", "model": "deepseek", "persona_id": "deepseek"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    event_names = [name for name, _ in events]
    assert "meta" in event_names
    assert "token" in event_names
    assert "done" in event_names

    meta = dict(events)["meta"]
    conv_id = meta["conversation_id"]
    tokens = "".join(payload["content"] for name, payload in events if name == "token")
    assert tokens == "你好，我是 Zoe！"

    # Verify DB persisted both user and assistant messages
    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=headers).json()
    assert detail["title"] == "嗨，打个招呼吧"
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["content"] == "你好，我是 Zoe！"

    # Second turn should pass prior history properly without duplicating user message
    fake_llm_2 = FakeStreamingLLM(["没问题！"])
    monkeypatch.setattr(model_registry, "get_chat_client", lambda model_id, temperature=0.7: fake_llm_2)
    resp2 = client.post(
        "/api/v1/chat/stream",
        json={"conversation_id": conv_id, "message": "帮我讲个笑话", "model": "deepseek"},
        headers=headers,
    )
    assert resp2.status_code == 200
    # System + prior User + prior Assistant + new User = 4 messages
    assert len(fake_llm_2.received_messages[0]) == 4

    # Regenerate replaces last assistant reply cleanly
    fake_llm_3 = FakeStreamingLLM(["换一个更好笑的笑话！"])
    monkeypatch.setattr(model_registry, "get_chat_client", lambda model_id, temperature=0.7: fake_llm_3)
    regen = client.post(
        "/api/v1/chat/stream",
        json={"conversation_id": conv_id, "model": "deepseek", "regenerate": True},
        headers=headers,
    )
    assert regen.status_code == 200
    detail_after_regen = client.get(f"/api/v1/conversations/{conv_id}", headers=headers).json()
    assert len(detail_after_regen["messages"]) == 4
    assert detail_after_regen["messages"][-1]["content"] == "换一个更好笑的笑话！"

    # Edit first user message truncates conversation and replays
    first_user_id = detail_after_regen["messages"][0]["id"]
    fake_llm_4 = FakeStreamingLLM(["编辑后的回复"])
    monkeypatch.setattr(model_registry, "get_chat_client", lambda model_id, temperature=0.7: fake_llm_4)
    edited = client.post(
        "/api/v1/chat/stream",
        json={
            "conversation_id": conv_id,
            "message": "新的第一条消息",
            "model": "deepseek",
            "edit_message_id": first_user_id,
        },
        headers=headers,
    )
    assert edited.status_code == 200
    detail_after_edit = client.get(f"/api/v1/conversations/{conv_id}", headers=headers).json()
    assert len(detail_after_edit["messages"]) == 2
    assert detail_after_edit["messages"][0]["content"] == "新的第一条消息"
    assert detail_after_edit["messages"][1]["content"] == "编辑后的回复"


def test_web_search_emits_sources_and_saves_them(client, monkeypatch):
    fake_llm = FakeStreamingLLM(["北京今天晴朗，22°C [1]。"])
    monkeypatch.setattr(model_registry, "get_chat_client", lambda model_id, temperature=0.7: fake_llm)
    monkeypatch.setattr(model_registry, "is_search_configured", lambda: True)

    async def _fake_search(query, max_results=None):
        return [
            {
                "title": "北京今日天气预报",
                "url": "https://weather.example.com/beijing",
                "content": "北京今天晴，最高气温22度",
                "published_date": "2026-11-23",
            }
        ]

    monkeypatch.setattr(chat_service, "search_web", _fake_search)

    headers = {"X-Guest-ID": "guest_search_1"}
    resp = client.post(
        "/api/v1/chat/stream",
        json={"message": "今天北京天气怎么样", "model": "deepseek", "web_search": "auto"},
        headers=headers,
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    sources_events = [p for name, p in events if name == "sources"]
    assert len(sources_events) == 1
    assert sources_events[0]["results"][0]["title"] == "北京今日天气预报"

    conv_id = dict(events)["meta"]["conversation_id"]
    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=headers).json()
    assert detail["messages"][1]["sources"][0]["url"] == "https://weather.example.com/beijing"


def test_image_generation_route_in_chat(client, monkeypatch):
    async def _fake_gen(prompt, model_id="qwen", wanx_size="1024*1024", doubao_size="2K", style=None):
        return "https://cdn.example.com/cat.png", "wanx"

    monkeypatch.setattr(chat_service, "generate_image", _fake_gen)

    headers = {"X-Guest-ID": "guest_img_1"}
    resp = client.post(
        "/api/v1/chat",
        json={"message": "帮我画一张橘猫插画", "model": "qwen"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "image"
    assert body["response"] == "https://cdn.example.com/cat.png"


def test_legacy_chat_deduplicates_trailing_user_history(client, monkeypatch):
    fake_llm = FakeStreamingLLM(["收到！"])
    monkeypatch.setattr(model_registry, "get_chat_client", lambda model_id, temperature=0.7: fake_llm)

    resp = client.post(
        "/chat",
        json={
            "message": "你好",
            "model": "deepseek",
            "history": [{"role": "user", "content": "你好"}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["response"] == "收到！"
    # SystemMessage + single HumanMessage (not duplicated!)
    assert len(fake_llm.received_messages[0]) == 2


def test_unconfigured_model_returns_graceful_sse_error(client, monkeypatch):
    monkeypatch.setattr(model_registry.settings, "deepseek_api_key", None)
    model_registry.clear_cache()

    resp = client.post(
        "/api/v1/chat/stream",
        json={"message": "你好", "model": "deepseek"},
        headers={"X-Guest-ID": "guest_unconf_1"},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    err_events = [p for name, p in events if name == "error"]
    assert len(err_events) == 1
    assert err_events[0]["code"] == "MODEL_NOT_CONFIGURED"


def test_vision_chat_and_delete_single_message(client, monkeypatch):
    fake_vision = FakeStreamingLLM(["这是一只可爱的橘猫。"])
    monkeypatch.setattr(model_registry, "get_vision_client", lambda temperature=0.7: fake_vision)

    headers = {"X-Guest-ID": "guest_vision_1"}
    resp = client.post(
        "/api/v1/chat/stream",
        json={
            "message": "图里有什么？",
            "model": "deepseek",
            "images": ["data:image/png;base64,iVBORw0KGgo="],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    tokens = "".join(p["content"] for name, p in events if name == "token")
    assert tokens == "这是一只可爱的橘猫。"

    conv_id = dict(events)["meta"]["conversation_id"]
    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=headers).json()
    assert len(detail["messages"]) == 2
    msg_id = detail["messages"][1]["id"]

    # Delete assistant message
    del_resp = client.delete(f"/api/v1/conversations/{conv_id}/messages/{msg_id}", headers=headers)
    assert del_resp.status_code == 204
    detail_after = client.get(f"/api/v1/conversations/{conv_id}", headers=headers).json()
    assert len(detail_after["messages"]) == 1

    # Clear all conversations
    clear_resp = client.delete("/api/v1/conversations", headers=headers)
    assert clear_resp.status_code == 204
    assert client.get("/api/v1/conversations", headers=headers).json()["total"] == 0

