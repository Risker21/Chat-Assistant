"""Application configuration powered by pydantic-settings."""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    """Resolve a writable default SQLite path for both local and serverless environments."""
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/chat_assistant.db"
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return "sqlite:///./data/chat_assistant.db"


class Settings(BaseSettings):
    """Centralized, validated application settings loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application metadata
    app_name: str = "解忧小铺 · AI 智能助手"
    app_version: str = "2.0.0"
    environment: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Server & CORS
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    cors_origins_raw: str = Field(default="*", alias="CORS_ORIGINS")

    # Database
    database_url: str = Field(default_factory=_default_database_url, alias="DATABASE_URL")

    # Security / JWT
    jwt_secret_key: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32),
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=60 * 24 * 7, alias="JWT_EXPIRE_MINUTES")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=60, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    # Chat defaults
    default_model: str = Field(default="deepseek", alias="DEFAULT_MODEL")
    max_history_messages: int = Field(default=20, alias="MAX_HISTORY_MESSAGES")
    max_upload_images: int = Field(default=4, alias="MAX_UPLOAD_IMAGES")
    request_timeout_seconds: int = Field(default=90, alias="REQUEST_TIMEOUT_SECONDS")

    # LLM Providers: DeepSeek
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1", alias="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    # LLM Providers: Alibaba DashScope (Qwen / Wanx)
    dashscope_api_key: Optional[str] = Field(default=None, alias="DASHSCOPE_API_KEY")
    dashscope_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="DASHSCOPE_BASE_URL",
    )
    qwen_model: str = Field(default="qwen-plus", alias="QWEN_MODEL")
    qwen_vision_model: str = Field(default="qwen-vl-max", alias="QWEN_VISION_MODEL")
    wanx_image_model: str = Field(default="wanx-v1", alias="WANX_IMAGE_MODEL")

    # LLM Providers: Zhipu GLM
    zhipu_api_key: Optional[str] = Field(default=None, alias="ZHIPU_API_KEY")
    zhipu_base_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        alias="ZHIPU_BASE_URL",
    )
    zhipu_model: str = Field(default="glm-5", alias="ZHIPU_MODEL")

    # LLM Providers: Tencent Hunyuan
    hunyuan_api_key: Optional[str] = Field(default=None, alias="HUNYUAN_API_KEY")
    hunyuan_base_url: str = Field(
        default="https://api.hunyuan.cloud.tencent.com/v1",
        alias="HUNYUAN_BASE_URL",
    )
    hunyuan_model: str = Field(default="hunyuan-turbos-latest", alias="HUNYUAN_MODEL")

    # LLM Providers: ByteDance Doubao / Ark
    doubao_api_key: Optional[str] = Field(default=None, alias="DOUBAO_API_KEY")
    ark_api_key: Optional[str] = Field(default=None, alias="ARK_API_KEY")
    doubao_base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3",
        alias="DOUBAO_BASE_URL",
    )
    doubao_model: str = Field(default="doubao-seed-1-8-251228", alias="DOUBAO_MODEL")
    doubao_image_model: str = Field(
        default="doubao-seedream-5-0-260128",
        alias="DOUBAO_IMAGE_MODEL",
    )

    # Web Search: Tavily
    tavily_api_key: Optional[str] = Field(default=None, alias="TAVILY_API_KEY")
    tavily_base_url: str = Field(default="https://api.tavily.com", alias="TAVILY_BASE_URL")
    tavily_max_results: int = Field(default=5, alias="TAVILY_MAX_RESULTS")

    @property
    def effective_doubao_api_key(self) -> Optional[str]:
        return self.doubao_api_key or self.ark_api_key

    @property
    def cors_origins(self) -> List[str]:
        raw = self.cors_origins_raw.strip()
        if not raw or raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
