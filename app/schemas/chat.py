"""Schemas for chat, streaming, search citations, and image generation."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class HistoryMessageItem(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class SearchResultItem(BaseModel):
    title: str
    url: str = ""
    content: str = ""
    published_date: str = ""


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=16000)
    conversation_id: Optional[str] = Field(default=None, max_length=64)
    model: str = Field(default="deepseek", max_length=32)
    persona_id: Optional[str] = Field(default=None, max_length=64)
    images: List[str] = Field(default_factory=list, max_length=4)
    web_search: Literal["auto", "on", "off"] = "auto"
    image_mode: Literal["auto", "generate", "edit", "off"] = "auto"
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_history: Optional[int] = Field(default=None, ge=0, le=60)
    system_prompt_override: Optional[str] = Field(default=None, max_length=4000)
    regenerate: bool = False
    edit_message_id: Optional[str] = None
    # Stateless fallback for legacy clients without conversation_id
    history: Optional[List[HistoryMessageItem]] = None


class ChatResponse(BaseModel):
    response: str
    type: Literal["text", "image", "error"] = "text"
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    title: Optional[str] = None
    thinking: Optional[str] = None
    prompt: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    latency_ms: Optional[int] = None


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    model: str = Field(default="qwen", max_length=32)
    size: str = Field(default="1024*1024", max_length=32)


class ImageGenerateResponse(BaseModel):
    image_url: str
    prompt: str
    provider: str
