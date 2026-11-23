"""Conversation management, message deletion, search, and export routes."""

from __future__ import annotations

import json
from typing import List, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import Identity, get_current_identity
from app.db.database import get_db
from app.db.models import Conversation, Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
    MessageResponse,
)

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


def _safe_json_load(raw: Optional[str]) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _message_to_schema(msg: Message) -> MessageResponse:
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        msg_type=msg.msg_type,
        model=msg.model,
        images=_safe_json_load(msg.images_json),
        image_url=msg.image_url,
        image_prompt=msg.image_prompt,
        sources=_safe_json_load(msg.sources_json),
        thinking=msg.thinking,
        latency_ms=msg.latency_ms,
        created_at=msg.created_at,
    )


def _get_owned_conversation(db: Session, owner_key: str, conversation_id: str) -> Conversation:
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.owner_key == owner_key)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    return conv


@router.get("")
def list_conversations(
    q: Optional[str] = Query(default=None, max_length=100, description="按标题或内容搜索"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    query = db.query(Conversation).filter(Conversation.owner_key == identity.owner_key)

    if q and q.strip():
        pattern = f"%{q.strip()}%"
        matching_conv_ids = (
            db.query(Message.conversation_id)
            .filter(Message.content.ilike(pattern))
            .distinct()
        )
        query = query.filter(
            (Conversation.title.ilike(pattern)) | (Conversation.id.in_(matching_conv_ids))
        )

    total = query.count()
    rows = (
        query.order_by(Conversation.pinned.desc(), Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    conv_ids = [c.id for c in rows]
    counts: dict[str, int] = {}
    previews: dict[str, str] = {}

    if conv_ids:
        count_rows = (
            db.query(Message.conversation_id, func.count(Message.id))
            .filter(Message.conversation_id.in_(conv_ids))
            .group_by(Message.conversation_id)
            .all()
        )
        counts = {cid: int(cnt) for cid, cnt in count_rows}

        # Fetch latest message preview per conversation
        for cid in conv_ids:
            last_msg = (
                db.query(Message)
                .filter(Message.conversation_id == cid)
                .order_by(Message.created_at.desc())
                .first()
            )
            if last_msg:
                text = (last_msg.content or last_msg.image_prompt or "").strip()
                previews[cid] = text[:80]

    items: List[ConversationSummary] = [
        ConversationSummary(
            id=c.id,
            title=c.title,
            model=c.model,
            persona_id=c.persona_id,
            temperature=c.temperature,
            pinned=c.pinned,
            message_count=counts.get(c.id, 0),
            last_message_preview=previews.get(c.id),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in rows
    ]
    return {"conversations": [item.model_dump() for item in items], "total": total}


@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    conv = Conversation(
        owner_key=identity.owner_key,
        title=(payload.title or "新对话").strip() or "新对话",
        model=payload.model,
        persona_id=payload.persona_id,
        system_prompt_override=payload.system_prompt_override,
        temperature=payload.temperature,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        persona_id=conv.persona_id,
        system_prompt_override=conv.system_prompt_override,
        temperature=conv.temperature,
        pinned=conv.pinned,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[],
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, identity.owner_key, conversation_id)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        persona_id=conv.persona_id,
        system_prompt_override=conv.system_prompt_override,
        temperature=conv.temperature,
        pinned=conv.pinned,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[_message_to_schema(m) for m in messages],
    )


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, identity.owner_key, conversation_id)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "title" and isinstance(value, str):
            value = value.strip() or conv.title
        setattr(conv, key, value)
    db.commit()
    db.refresh(conv)
    msg_count = db.query(func.count(Message.id)).filter(Message.conversation_id == conv.id).scalar() or 0
    return ConversationSummary(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        persona_id=conv.persona_id,
        temperature=conv.temperature,
        pinned=conv.pinned,
        message_count=int(msg_count),
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, identity.owner_key, conversation_id)
    db.delete(conv)
    db.commit()
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_conversations(
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    convs = db.query(Conversation).filter(Conversation.owner_key == identity.owner_key).all()
    for conv in convs:
        db.delete(conv)
    db.commit()
    return None


@router.delete("/{conversation_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    conversation_id: str,
    message_id: str,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, identity.owner_key, conversation_id)
    msg = (
        db.query(Message)
        .filter(Message.id == message_id, Message.conversation_id == conv.id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    db.delete(msg)
    db.commit()
    return None


@router.get("/{conversation_id}/export")
def export_conversation(
    conversation_id: str,
    format: Literal["markdown", "json"] = Query(default="markdown"),
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, identity.owner_key, conversation_id)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    safe_name = quote(f"{conv.title}.{ 'md' if format == 'markdown' else 'json' }")

    if format == "json":
        payload = {
            "id": conv.id,
            "title": conv.title,
            "model": conv.model,
            "persona_id": conv.persona_id,
            "created_at": conv.created_at.isoformat(),
            "messages": [_message_to_schema(m).model_dump(mode="json") for m in messages],
        }
        return Response(
            content=json.dumps(payload, ensure_ascii=False, indent=2),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
        )

    lines = [
        f"# {conv.title}",
        "",
        f"- 模型: `{conv.model}`",
        f"- 角色: `{conv.persona_id}`",
        f"- 创建时间: {conv.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "---",
        "",
    ]
    for msg in messages:
        role_label = "用户" if msg.role == "user" else f"AI ({msg.model or conv.model})"
        lines.append(f"## {role_label}")
        lines.append("")
        if msg.msg_type == "image" and msg.image_url:
            lines.append(f"> 提示词: {msg.image_prompt or msg.content}")
            lines.append("")
            lines.append(f"![Generated Image]({msg.image_url})")
        else:
            lines.append(msg.content)
        sources = _safe_json_load(msg.sources_json)
        if sources:
            lines.append("")
            lines.append("**参考来源：**")
            for idx, src in enumerate(sources, start=1):
                lines.append(f"- [{idx}] [{src.get('title', '链接')}]({src.get('url', '')})")
        lines.append("")

    return Response(
        content="\n".join(lines),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )
