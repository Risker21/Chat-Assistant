"""Lazy-loaded LLM client registry with provider availability checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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
        self._vision_client: Optional[Any] = None

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
        """Return a LangChain chat model instance for `model_id` configured with `temperature`."""
        if model_id not in MODEL_SPECS:
            raise ModelNotFoundError(model_id)

        spec = MODEL_SPECS[model_id]
        api_key, base_url, model_name = self._provider_credentials(model_id)
        if not api_key or not api_key.strip():
            raise ModelNotConfiguredError(spec.label, spec.env_hint)

        cache_key = f"{model_id}:{round(float(temperature), 2)}"
        if cache_key in self._clients:
            return self._clients[cache_key]

        from langchain_openai import ChatOpenAI

        client = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=float(temperature),
            timeout=self.settings.request_timeout_seconds,
            max_retries=2,
            streaming=True,
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

        from langchain_openai import ChatOpenAI

        client = ChatOpenAI(
            model=s.qwen_vision_model,
            api_key=s.dashscope_api_key,
            base_url=s.dashscope_base_url,
            temperature=float(temperature),
            timeout=s.request_timeout_seconds,
            max_retries=2,
            streaming=True,
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
        self._vision_client = None


model_registry = ModelRegistry()
