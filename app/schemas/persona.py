"""Schemas for models and personas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StarterPrompt(BaseModel):
    title: str
    prompt: str
    icon: str = "fa-sparkles"
    color: str = "violet"


class ModelInfo(BaseModel):
    value: str
    label: str
    provider: str
    model_name: str
    configured: bool
    supports_vision: bool = False
    supports_image_gen: bool = False
    supports_stream: bool = True
    default_persona_id: str


class PersonaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=64)
    description: str = Field(default="", max_length=500)
    system_prompt: str = Field(..., min_length=1, max_length=4000)
    default_model: str = Field(default="deepseek", max_length=32)
    icon: str = Field(default="fa-sparkles", max_length=64)
    bg_gradient: str = Field(
        default="bg-gradient-to-br from-violet-500 to-indigo-600", max_length=128
    )
    starters: List[StarterPrompt] = Field(default_factory=list)


class PersonaCreate(PersonaBase):
    pass


class PersonaUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    title: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=500)
    system_prompt: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    default_model: Optional[str] = Field(default=None, max_length=32)
    icon: Optional[str] = Field(default=None, max_length=64)
    bg_gradient: Optional[str] = Field(default=None, max_length=128)
    starters: Optional[List[StarterPrompt]] = None


class PersonaResponse(PersonaBase):
    id: str
    is_builtin: bool = False
    greeting: Optional[str] = None
    created_at: Optional[datetime] = None
