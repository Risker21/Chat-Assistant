"""Schemas for conversations and persisted messages."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    msg_type: str = "text"
    model: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    thinking: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default="新对话", max_length=200)
    model: str = Field(default="deepseek", max_length=32)
    persona_id: str = Field(default="deepseek", max_length=64)
    system_prompt_override: Optional[str] = Field(default=None, max_length=4000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    model: Optional[str] = Field(default=None, max_length=32)
    persona_id: Optional[str] = Field(default=None, max_length=64)
    system_prompt_override: Optional[str] = Field(default=None, max_length=4000)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    pinned: Optional[bool] = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    model: str
    persona_id: str
    temperature: float
    pinned: bool
    message_count: int = 0
    last_message_preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    id: str
    title: str
    model: str
    persona_id: str
    system_prompt_override: Optional[str] = None
    temperature: float
    pinned: bool
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)
