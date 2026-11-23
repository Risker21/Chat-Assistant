"""Core chat orchestration service supporting SSE streaming, persistence, search, and multimodal."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from fastapi import Request
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Conversation, Message
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.image_service import edit_image_with_vision, generate_image
from app.services.intent_service import detect_intent
from app.services.model_registry import ModelError, model_registry
from app.services.persona_service import resolve_system_prompt
from app.services.search_service import format_search_context, search_web

logger = get_logger(__name__)


def _normalize_data_url(img: str) -> str:
    if img.startswith("data:image") or img.startswith("http://") or img.startswith("https://"):
        return img
    return f"data:image/jpeg;base64,{img}"


def _derive_title(message: str, has_images: bool) -> str:
    cleaned = " ".join((message or "").split())
    if not cleaned:
        return "图片对话" if has_images else "新对话"
    return cleaned[:28] + ("..." if len(cleaned) > 28 else "")


def format_sse(event: str, data: Dict[str, Any]) -> str:
    """Format a server-sent event payload."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_chunk_text(chunk: Any) -> str:
    if chunk is None:
        return ""
    if isinstance(chunk, str):
        return chunk
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return str(content)


def _prepare_conversation_and_history(
    db: Session,
    owner_key: str,
    req: ChatRequest,
    persist: bool,
) -> Tuple[Optional[Conversation], Optional[Message], str, List[str], List[Dict[str, str]]]:
    """Load/create conversation, handle regenerate/edit, persist user message, and return history."""
    settings = get_settings()
    max_history = req.max_history if req.max_history is not None else settings.max_history_messages
    user_text = (req.message or "").strip()
    images = list(req.images or [])[: settings.max_upload_images]

    if not persist:
        history_items: List[Dict[str, str]] = []
        if req.history:
            raw_hist = [{"role": h.role, "content": h.content} for h in req.history]
            # Legacy frontend pushed current user message into history before POSTing
            if raw_hist and raw_hist[-1]["role"] == "user" and raw_hist[-1]["content"].strip() == user_text:
                raw_hist = raw_hist[:-1]
            history_items = raw_hist[-max_history:] if max_history > 0 else []
        return None, None, user_text, images, history_items

    conversation: Optional[Conversation] = None
    if req.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == req.conversation_id, Conversation.owner_key == owner_key)
            .first()
        )
        if not conversation:
            raise ModelError("会话不存在或无权访问", code="CONVERSATION_NOT_FOUND", status_code=404)
        # Keep conversation model/persona synced with latest selection
        conversation.model = req.model
        if req.persona_id:
            conversation.persona_id = req.persona_id
        if req.temperature is not None:
            conversation.temperature = req.temperature
    else:
        persona_id = req.persona_id or req.model
        conversation = Conversation(
            owner_key=owner_key,
            title=_derive_title(user_text, bool(images)),
            model=req.model,
            persona_id=persona_id,
            system_prompt_override=req.system_prompt_override or None,
            temperature=req.temperature if req.temperature is not None else 0.7,
        )
        db.add(conversation)
        db.flush()

    existing_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    user_msg: Optional[Message] = None

    if req.regenerate:
        # Locate last user message and remove assistant replies after it
        last_user_idx = -1
        for idx in range(len(existing_messages) - 1, -1, -1):
            if existing_messages[idx].role == "user":
                last_user_idx = idx
                break
        if last_user_idx == -1:
            raise ModelError("当前会话没有可重新生成的用户消息", code="NOTHING_TO_REGENERATE", status_code=400)

        user_msg = existing_messages[last_user_idx]
        user_text = user_msg.content
        if user_msg.images_json:
            try:
                images = json.loads(user_msg.images_json)
            except Exception:
                images = []
        for trailing in existing_messages[last_user_idx + 1 :]:
            db.delete(trailing)
        prior_messages = existing_messages[:last_user_idx]
    else:
        if req.edit_message_id:
            target_idx = next(
                (i for i, m in enumerate(existing_messages) if m.id == req.edit_message_id), -1
            )
            if target_idx == -1:
                raise ModelError("要编辑的消息不存在", code="MESSAGE_NOT_FOUND", status_code=404)
            for trailing in existing_messages[target_idx:]:
                db.delete(trailing)
            prior_messages = existing_messages[:target_idx]
        else:
            prior_messages = existing_messages

        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=user_text or ("[图片]" if images else ""),
            msg_type="text",
            images_json=json.dumps(images) if images else None,
        )
        db.add(user_msg)

        if conversation.title in ("新对话", "") and (user_text or images):
            conversation.title = _derive_title(user_text, bool(images))

    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversation)
    if user_msg:
        db.refresh(user_msg)

    history_items = []
    if max_history > 0:
        for msg in prior_messages[-max_history:]:
            if msg.role in ("user", "assistant") and msg.msg_type != "error":
                content_text = msg.content or (
                    f"[已生成图片: {msg.image_prompt or ''}]" if msg.msg_type == "image" else ""
                )
                if content_text:
                    history_items.append({"role": msg.role, "content": content_text})

    return conversation, user_msg, user_text, images, history_items


def _build_langchain_messages(
    system_prompt: str,
    history: List[Dict[str, str]],
    user_text: str,
    images: List[str] | None = None,
) -> List[BaseMessage]:
    messages: List[BaseMessage] = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))

    for item in history:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        elif item["role"] == "assistant":
            messages.append(AIMessage(content=item["content"]))

    if images:
        parts: List[Dict[str, Any]] = [
            {"type": "text", "text": user_text or "请帮我详细解读这张图片的内容。"}
        ]
        for img in images:
            parts.append({"type": "image_url", "image_url": {"url": _normalize_data_url(img)}})
        messages.append(HumanMessage(content=parts))
    else:
        messages.append(HumanMessage(content=user_text))

    return messages


def _save_assistant_message(
    db: Session,
    conversation: Optional[Conversation],
    *,
    content: str,
    msg_type: str = "text",
    model: Optional[str] = None,
    image_url: Optional[str] = None,
    image_prompt: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    thinking: Optional[str] = None,
    latency_ms: Optional[int] = None,
) -> Optional[Message]:
    if not conversation:
        return None
    msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=content,
        msg_type=msg_type,
        model=model,
        image_url=image_url,
        image_prompt=image_prompt,
        sources_json=json.dumps(sources, ensure_ascii=False) if sources else None,
        thinking=thinking,
        latency_ms=latency_ms,
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


async def stream_chat_events(
    db: Session,
    owner_key: str,
    req: ChatRequest,
    http_request: Optional[Request] = None,
    persist: bool = True,
) -> AsyncGenerator[Tuple[str, Dict[str, Any]], None]:
    """Execute chat workflow and yield structured `(event_name, payload)` tuples."""
    start_time = time.perf_counter()

    if not req.regenerate and not (req.message or "").strip() and not req.images:
        yield ("error", {"message": "请输入消息或上传图片", "code": "EMPTY_INPUT"})
        return

    try:
        conversation, user_msg, user_text, images, history = _prepare_conversation_and_history(
            db, owner_key, req, persist=persist
        )
    except ModelError as exc:
        yield ("error", {"message": exc.message, "code": exc.code})
        return

    if conversation:
        yield (
            "meta",
            {
                "conversation_id": conversation.id,
                "user_message_id": user_msg.id if user_msg else None,
                "title": conversation.title,
                "model": conversation.model,
                "persona_id": conversation.persona_id,
            },
        )

    active_persona_id = req.persona_id or (conversation.persona_id if conversation else req.model)
    temperature = (
        req.temperature
        if req.temperature is not None
        else (conversation.temperature if conversation else 0.7)
    )
    system_prompt = resolve_system_prompt(
        db=db,
        owner_key=owner_key,
        persona_id=active_persona_id,
        model_id=req.model,
        override_prompt=conversation.system_prompt_override if conversation else None,
    )

    intent = detect_intent(
        message=user_text,
        has_images=bool(images),
        web_search_mode=req.web_search,
        image_mode=req.image_mode,
    )
    logger.info(
        "Chat intent=%s reason=%s model=%s persona=%s has_images=%s",
        intent.kind,
        intent.reason,
        req.model,
        active_persona_id,
        bool(images),
    )

    try:
        # --- Route 1: Image Editing ---
        if intent.kind == "image_edit" and images:
            yield ("status", {"stage": "analyzing_image", "message": f"正在分析图片并进行{intent.edit_type}..."})
            image_url, display_prompt, provider = await edit_image_with_vision(
                images=images,
                user_instruction=user_text,
                edit_type=intent.edit_type or "图片编辑",
                model_id=req.model,
                wanx_size=intent.image_size,
                doubao_size=intent.doubao_size,
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            saved = _save_assistant_message(
                db,
                conversation,
                content=display_prompt,
                msg_type="image",
                model=provider,
                image_url=image_url,
                image_prompt=display_prompt,
                latency_ms=latency_ms,
            )
            yield ("image", {"url": image_url, "prompt": display_prompt, "provider": provider})
            yield (
                "done",
                {
                    "conversation_id": conversation.id if conversation else None,
                    "message_id": saved.id if saved else None,
                    "title": conversation.title if conversation else None,
                    "type": "image",
                    "latency_ms": latency_ms,
                },
            )
            return

        # --- Route 2: Text-to-Image Generation ---
        if intent.kind == "image_generate":
            yield ("status", {"stage": "generating_image", "message": "正在为您精心绘制图片，请稍候..."})
            image_url, provider = await generate_image(
                prompt=user_text,
                model_id=req.model,
                wanx_size=intent.image_size,
                doubao_size=intent.doubao_size,
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            saved = _save_assistant_message(
                db,
                conversation,
                content=user_text,
                msg_type="image",
                model=provider,
                image_url=image_url,
                image_prompt=user_text,
                latency_ms=latency_ms,
            )
            yield ("image", {"url": image_url, "prompt": user_text, "provider": provider})
            yield (
                "done",
                {
                    "conversation_id": conversation.id if conversation else None,
                    "message_id": saved.id if saved else None,
                    "title": conversation.title if conversation else None,
                    "type": "image",
                    "latency_ms": latency_ms,
                },
            )
            return

        # --- Route 3: Web Search Grounding (if requested or auto-detected) ---
        search_results: List[Dict[str, Any]] = []
        effective_user_text = user_text
        effective_system_prompt = system_prompt

        if intent.kind == "web_search":
            if model_registry.is_search_configured():
                yield ("status", {"stage": "searching", "message": "正在联网检索最新资料..."})
                search_results = await search_web(user_text)
                if search_results:
                    yield ("sources", {"results": search_results})
                    effective_system_prompt = (
                        f"{system_prompt}\n\n"
                        "当提供了实时搜索结果时，请优先依据搜索结果准确回答，"
                        "如与内置知识冲突以搜索结果为准，并自然融入 [1]、[2] 等来源引用。"
                    )
                    effective_user_text = (
                        f"{user_text}\n\n{format_search_context(search_results)}"
                    )
            elif req.web_search == "on":
                yield (
                    "status",
                    {
                        "stage": "thinking",
                        "message": "未配置 TAVILY_API_KEY，已自动切换为模型直接回答...",
                    },
                )

        # --- Route 4: Vision Chat or Standard Text Chat (Streaming) ---
        if intent.kind == "vision_chat" and images:
            yield ("status", {"stage": "analyzing_image", "message": "正在识别并理解图片内容..."})
            llm = model_registry.get_vision_client(temperature=temperature)
            lc_messages = _build_langchain_messages(
                effective_system_prompt, history, effective_user_text, images=images
            )
            used_model = "qwen-vl"
        else:
            if not search_results:
                yield ("status", {"stage": "thinking", "message": "正在思考回复..."})
            llm = model_registry.get_chat_client(req.model, temperature=temperature)
            lc_messages = _build_langchain_messages(
                effective_system_prompt, history, effective_user_text
            )
            used_model = req.model

        collected_chunks: List[str] = []
        aborted = False

        if hasattr(llm, "astream"):
            async for chunk in llm.astream(lc_messages):
                if http_request is not None and await http_request.is_disconnected():
                    aborted = True
                    break
                token = _extract_chunk_text(chunk)
                if token:
                    collected_chunks.append(token)
                    yield ("token", {"content": token})
        else:
            response = await llm.ainvoke(lc_messages)
            full_text = _extract_chunk_text(response)
            if full_text:
                collected_chunks.append(full_text)
                yield ("token", {"content": full_text})

        full_reply = "".join(collected_chunks)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        saved = None
        if full_reply or not aborted:
            saved = _save_assistant_message(
                db,
                conversation,
                content=full_reply or "（生成已停止）",
                msg_type="text",
                model=used_model,
                sources=search_results or None,
                latency_ms=latency_ms,
            )

        if not aborted:
            yield (
                "done",
                {
                    "conversation_id": conversation.id if conversation else None,
                    "message_id": saved.id if saved else None,
                    "title": conversation.title if conversation else None,
                    "type": "text",
                    "aborted": False,
                    "latency_ms": latency_ms,
                },
            )

    except ModelError as exc:
        logger.warning("Chat model error code=%s msg=%s", exc.code, exc.message)
        yield ("error", {"message": exc.message, "code": exc.code})
    except Exception as exc:
        logger.exception("Unexpected error during chat stream: %s", exc)
        yield (
            "error",
            {
                "message": "抱歉，模型调用暂时遇到异常，请检查 API 配置或稍后重试。",
                "code": "INTERNAL_ERROR",
            },
        )


async def complete_chat(
    db: Session,
    owner_key: str,
    req: ChatRequest,
    persist: bool = True,
) -> ChatResponse:
    """Non-streaming wrapper around `stream_chat_events` for standard REST clients."""
    tokens: List[str] = []
    sources: List[Dict[str, Any]] = []
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    conversation_id: Optional[str] = req.conversation_id
    message_id: Optional[str] = None
    title: Optional[str] = None
    latency_ms: Optional[int] = None
    last_status: Optional[str] = None

    async for event_name, payload in stream_chat_events(
        db=db, owner_key=owner_key, req=req, persist=persist
    ):
        if event_name == "meta":
            conversation_id = payload.get("conversation_id")
            title = payload.get("title")
        elif event_name == "status":
            last_status = payload.get("message")
        elif event_name == "sources":
            sources = payload.get("results", [])
        elif event_name == "token":
            tokens.append(payload.get("content", ""))
        elif event_name == "image":
            image_url = payload.get("url")
            image_prompt = payload.get("prompt")
        elif event_name == "done":
            message_id = payload.get("message_id")
            title = payload.get("title") or title
            latency_ms = payload.get("latency_ms")
        elif event_name == "error":
            return ChatResponse(
                response=payload.get("message", "请求失败"),
                type="error",
                conversation_id=conversation_id,
                title=title,
            )

    if image_url:
        return ChatResponse(
            response=image_url,
            type="image",
            conversation_id=conversation_id,
            message_id=message_id,
            title=title,
            prompt=image_prompt,
            latency_ms=latency_ms,
        )

    return ChatResponse(
        response="".join(tokens),
        type="text",
        conversation_id=conversation_id,
        message_id=message_id,
        title=title,
        thinking=last_status,
        search_results=sources,
        latency_ms=latency_ms,
    )
