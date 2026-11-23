"""Lazy-loaded OpenAI-compatible async LLM registry powered by httpx."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.persona import ModelInfo

logger = get_logger(__name__)


class ModelError(Exception):
    """Base error for model resolution and invocation."""

    def __init__(self, message: str, code: str = "MODEL_ERROR", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ModelNotFoundError(ModelError):
    def __init__(self, model_id: str) -> None:
        super().__init__(
            message=f"不支持的模型: {model_id}",
            code="MODEL_NOT_FOUND",
            status_code=400,
        )


class ModelNotConfiguredError(ModelError):
    def __init__(self, model_id: str, env_hint: str) -> None:
        super().__init__(
            message=f"模型 {model_id} 尚未配置 API Key，请在 .env 中设置 {env_hint} 后重试。",
            code="MODEL_NOT_CONFIGURED",
            status_code=503,
        )


@dataclass
class StreamChunk:
    """Minimal chunk object matching LangChain's `.content` convention."""

    content: str


def _serialize_messages(messages: List[Any]) -> List[Dict[str, Any]]:
    """Convert LangChain BaseMessage objects or plain dicts to OpenAI Chat Completions format."""
    serialized: List[Dict[str, Any]] = []
    role_map = {
        "system": "system",
        "human": "user",
        "user": "user",
        "ai": "assistant",
        "assistant": "assistant",
    }
    for msg in messages:
        if isinstance(msg, dict):
            role = role_map.get(str(msg.get("role", "user")).lower(), "user")
            serialized.append({"role": role, "content": msg.get("content", "")})
        else:
            msg_type = getattr(msg, "type", "user")
            role = role_map.get(str(msg_type).lower(), "user")
            serialized.append({"role": role, "content": getattr(msg, "content", "")})
    return serialized


def _extract_upstream_error(status_code: int, body_text: str) -> str:
    try:
        data = json.loads(body_text)
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict) and err.get("message"):
                return f"上游模型返回错误 ({status_code}): {err['message']}"
            if data.get("message"):
                return f"上游模型返回错误 ({status_code}): {data['message']}"
    except Exception:
        pass
    snippet = (body_text or "").strip()[:200]
    return f"上游模型请求失败 (HTTP {status_code}){': ' + snippet if snippet else ''}"


class OpenAICompatibleChatClient:
    """Lightweight async streaming client for OpenAI-compatible Chat Completions APIs.

    Works uniformly with DeepSeek, DashScope (Qwen / Qwen-VL), Zhipu GLM, Tencent Hunyuan,
    and ByteDance Doubao/Ark without requiring the heavy `openai` or `langchain-openai` packages.
    """

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.7,
        timeout: int = 90,
    ) -> None:
        self.model = model
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.temperature = float(temperature)
        self.timeout = timeout

    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

    async def astream(self, messages: List[Any]) -> AsyncGenerator[StreamChunk, None]:
        payload = {
            "model": self.model,
            "messages": _serialize_messages(messages),
            "temperature": self.temperature,
            "stream": True,
        }
        timeout = httpx.Timeout(connect=15.0, read=float(self.timeout), write=30.0, pool=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", self._endpoint(), headers=self._headers(), json=payload
            ) as response:
                if response.status_code >= 400:
                    err_body = (await response.aread()).decode("utf-8", errors="ignore")
                    raise ModelError(
                        _extract_upstream_error(response.status_code, err_body),
                        code="UPSTREAM_API_ERROR",
                        status_code=502,
                    )

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk_json.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    text = delta.get("content")
                    if text:
                        yield StreamChunk(content=str(text))

    async def ainvoke(self, messages: List[Any]) -> StreamChunk:
        payload = {
            "model": self.model,
            "messages": _serialize_messages(messages),
            "temperature": self.temperature,
            "stream": False,
        }
        timeout = httpx.Timeout(connect=15.0, read=float(self.timeout), write=30.0, pool=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self._endpoint(),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if response.status_code >= 400:
                raise ModelError(
                    _extract_upstream_error(response.status_code, response.text),
                    code="UPSTREAM_API_ERROR",
                    status_code=502,
                )
            data = response.json()
            choices = data.get("choices") or []
            if choices:
                content = (choices[0].get("message") or {}).get("content", "")
                return StreamChunk(content=str(content))
            return StreamChunk(content="")


@dataclass(frozen=True)
class ModelSpec:
    value: str
    label: str
    provider: str
    env_hint: str
    default_persona_id: str
    supports_vision: bool = False
    supports_image_gen: bool = False


MODEL_SPECS: Dict[str, ModelSpec] = {
    "deepseek": ModelSpec(
        value="deepseek",
        label="DeepSeek",
        provider="deepseek",
        env_hint="DEEPSEEK_API_KEY",
        default_persona_id="deepseek",
        supports_vision=False,
        supports_image_gen=False,
    ),
    "qwen": ModelSpec(
        value="qwen",
        label="通义千问",
        provider="dashscope",
        env_hint="DASHSCOPE_API_KEY",
        default_persona_id="qwen",
        supports_vision=True,
        supports_image_gen=True,
    ),
    "hunyuan": ModelSpec(
        value="hunyuan",
        label="腾讯混元",
        provider="hunyuan",
        env_hint="HUNYUAN_API_KEY",
        default_persona_id="hunyuan",
        supports_vision=False,
        supports_image_gen=False,
    ),
    "glm": ModelSpec(
        value="glm",
        label="智谱 GLM",
        provider="zhipu",
        env_hint="ZHIPU_API_KEY",
        default_persona_id="glm",
        supports_vision=False,
        supports_image_gen=False,
    ),
    "doubao": ModelSpec(
        value="doubao",
        label="字节豆包",
        provider="doubao",
        env_hint="DOUBAO_API_KEY",
        default_persona_id="doubao",
        supports_vision=False,
        supports_image_gen=True,
    ),
}


class ModelRegistry:
    """Lazily initializes and caches LLM clients so missing keys never crash startup."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings
        self._clients: Dict[str, Any] = {}

    @property
    def settings(self) -> Settings:
        return self._settings or get_settings()

    def _provider_credentials(self, model_id: str) -> tuple[Optional[str], str, str]:
        s = self.settings
        if model_id == "deepseek":
            return s.deepseek_api_key, s.deepseek_base_url, s.deepseek_model
        if model_id == "qwen":
            return s.dashscope_api_key, s.dashscope_base_url, s.qwen_model
        if model_id == "glm":
            return s.zhipu_api_key, s.zhipu_base_url, s.zhipu_model
        if model_id == "hunyuan":
            return s.hunyuan_api_key, s.hunyuan_base_url, s.hunyuan_model
        if model_id == "doubao":
            return s.effective_doubao_api_key, s.doubao_base_url, s.doubao_model
        raise ModelNotFoundError(model_id)

    def is_configured(self, model_id: str) -> bool:
        if model_id not in MODEL_SPECS:
            return False
        api_key, _, _ = self._provider_credentials(model_id)
        return bool(api_key and api_key.strip())

    def is_vision_configured(self) -> bool:
        return bool(self.settings.dashscope_api_key and self.settings.dashscope_api_key.strip())

    def is_search_configured(self) -> bool:
        return bool(self.settings.tavily_api_key and self.settings.tavily_api_key.strip())

    def list_models(self) -> List[ModelInfo]:
        result: List[ModelInfo] = []
        for model_id, spec in MODEL_SPECS.items():
            api_key, _, model_name = self._provider_credentials(model_id)
            result.append(
                ModelInfo(
                    value=spec.value,
                    label=spec.label,
                    provider=spec.provider,
                    model_name=model_name,
                    configured=bool(api_key and api_key.strip()),
                    supports_vision=spec.supports_vision or self.is_vision_configured(),
                    supports_image_gen=spec.supports_image_gen or self.is_vision_configured(),
                    supports_stream=True,
                    default_persona_id=spec.default_persona_id,
                )
            )
        return result

    def get_chat_client(self, model_id: str, temperature: float = 0.7) -> Any:
        """Return an async OpenAI-compatible client for `model_id`."""
        if model_id not in MODEL_SPECS:
            raise ModelNotFoundError(model_id)

        spec = MODEL_SPECS[model_id]
        api_key, base_url, model_name = self._provider_credentials(model_id)
        if not api_key or not api_key.strip():
            raise ModelNotConfiguredError(spec.label, spec.env_hint)

        cache_key = f"{model_id}:{round(float(temperature), 2)}"
        if cache_key in self._clients:
            return self._clients[cache_key]

        client = OpenAICompatibleChatClient(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=float(temperature),
            timeout=self.settings.request_timeout_seconds,
        )
        self._clients[cache_key] = client
        logger.info("Initialized LLM client model_id=%s model=%s", model_id, model_name)
        return client

    def get_vision_client(self, temperature: float = 0.7) -> Any:
        """Return the DashScope Qwen-VL client for multimodal image understanding."""
        s = self.settings
        if not s.dashscope_api_key or not s.dashscope_api_key.strip():
            raise ModelNotConfiguredError("多模态视觉理解 (Qwen-VL)", "DASHSCOPE_API_KEY")

        cache_key = f"vision:{round(float(temperature), 2)}"
        if cache_key in self._clients:
            return self._clients[cache_key]

        client = OpenAICompatibleChatClient(
            model=s.qwen_vision_model,
            api_key=s.dashscope_api_key,
            base_url=s.dashscope_base_url,
            temperature=float(temperature),
            timeout=self.settings.request_timeout_seconds,
        )
        self._clients[cache_key] = client
        logger.info("Initialized Vision LLM client model=%s", s.qwen_vision_model)
        return client

    def get_fallback_text_model(self, preferred: str) -> str:
        """Pick preferred model if configured; otherwise fall back to first configured model."""
        if self.is_configured(preferred):
            return preferred
        for model_id in MODEL_SPECS:
            if self.is_configured(model_id):
                return model_id
        return preferred

    def clear_cache(self) -> None:
        self._clients.clear()


model_registry = ModelRegistry()
