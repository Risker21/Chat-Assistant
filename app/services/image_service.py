"""Async image generation and vision-guided image editing service."""

from __future__ import annotations

import asyncio
import re
from typing import List, Tuple

from langchain_core.messages import HumanMessage

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.model_registry import ModelError, ModelNotConfiguredError, model_registry

logger = get_logger(__name__)


def _normalize_data_url(img: str) -> str:
    if img.startswith("data:image") or img.startswith("http://") or img.startswith("https://"):
        return img
    return f"data:image/jpeg;base64,{img}"


def _build_edit_prompt(image_description: str, edit_type: str, user_request: str) -> Tuple[str, str]:
    """Compose a high-quality generation prompt from vision analysis + user edit instruction."""
    detail = user_request.strip()
    extract_match = re.search(
        r"(转换成|转成|变成|换成|改为|替换为|调整|优化|添加|加上|移除|删除|去掉|滤镜)([^，。！？]+)",
        user_request,
    )
    if extract_match:
        detail = extract_match.group(2).strip() or detail

    templates = {
        "风格转换": (
            f"{image_description}。将这个画面转换成{detail}风格，"
            "要求主体特征与构图保持一致、线条与色彩富有艺术表现力、光线自然、细节丰富。"
        ),
        "背景替换": (
            f"{image_description}。保持主体人物/物体外观不变，将背景自然替换为{detail}，"
            "要求主体边缘干净、光影与新背景协调统一、真实自然。"
        ),
        "调整优化": (
            f"{image_description}。按以下要求优化画面：{detail}，"
            "要求色彩饱满、对比度适中、清晰度高、整体质感专业。"
        ),
        "添加元素": (
            f"{image_description}。在画面中自然融入{detail}，"
            "要求位置比例合理、光影融合协调、不破坏原有主体。"
        ),
        "移除元素": (
            f"{image_description}。干净移除画面中的{detail}，"
            "并用周围自然协调的背景进行修补，画面完整无违和感。"
        ),
        "滤镜效果": (
            f"{image_description}。为画面施加{detail}视觉滤镜，"
            "要求色调统一、氛围感强烈且保留画面层次细节。"
        ),
    }
    prompt = templates.get(
        edit_type,
        f"{image_description}。根据用户要求编辑画面：{user_request}。要求自然协调、细节丰富、成片质感高。",
    )
    return prompt, detail


def _generate_with_doubao_sync(prompt: str, size: str) -> str:
    from openai import OpenAI

    settings = get_settings()
    api_key = settings.effective_doubao_api_key
    if not api_key:
        raise ModelNotConfiguredError("豆包绘图", "DOUBAO_API_KEY")

    client = OpenAI(base_url=settings.doubao_base_url, api_key=api_key)
    response = client.images.generate(
        model=settings.doubao_image_model,
        prompt=prompt,
        size=size,
        response_format="url",
        extra_body={"watermark": True, "quality": "high"},
    )
    if response.data and response.data[0].url:
        return response.data[0].url
    raise ModelError("豆包未能返回有效的图片链接", code="IMAGE_GEN_FAILED", status_code=502)


def _generate_with_wanx_sync(prompt: str, size: str, style: str | None = None) -> str:
    import dashscope
    from dashscope import ImageSynthesis

    settings = get_settings()
    if not settings.dashscope_api_key:
        raise ModelNotConfiguredError("通义万相绘图", "DASHSCOPE_API_KEY")

    dashscope.api_key = settings.dashscope_api_key
    wanx_size = size if "*" in size else "1024*1024"
    kwargs = {
        "model": settings.wanx_image_model,
        "prompt": prompt,
        "size": wanx_size,
        "n": 1,
    }
    if style:
        kwargs["style"] = style

    response = ImageSynthesis.call(**kwargs)
    if getattr(response, "status_code", None) != 200:
        err_msg = getattr(response, "message", "未知错误")
        raise ModelError(f"通义万相绘图失败: {err_msg}", code="IMAGE_GEN_FAILED", status_code=502)

    if response.output and getattr(response.output, "results", None):
        return response.output.results[0].url
    raise ModelError("未能获取生成的图片链接", code="IMAGE_GEN_FAILED", status_code=502)


async def generate_image(
    prompt: str,
    model_id: str = "qwen",
    wanx_size: str = "1024*1024",
    doubao_size: str = "2K",
    style: str | None = None,
) -> Tuple[str, str]:
    """Generate an image asynchronously, returning `(image_url, provider_name)`."""
    settings = get_settings()
    use_doubao = model_id == "doubao" and bool(settings.effective_doubao_api_key)

    if use_doubao:
        logger.info("Generating image via Doubao size=%s", doubao_size)
        url = await asyncio.to_thread(_generate_with_doubao_sync, prompt, doubao_size)
        return url, "doubao"

    if settings.dashscope_api_key:
        logger.info("Generating image via DashScope Wanx size=%s", wanx_size)
        url = await asyncio.to_thread(_generate_with_wanx_sync, prompt, wanx_size, style)
        return url, "wanx"

    if settings.effective_doubao_api_key:
        logger.info("Falling back to Doubao image generation size=%s", doubao_size)
        url = await asyncio.to_thread(_generate_with_doubao_sync, prompt, doubao_size)
        return url, "doubao"

    raise ModelNotConfiguredError("图片生成", "DASHSCOPE_API_KEY 或 DOUBAO_API_KEY")


async def edit_image_with_vision(
    images: List[str],
    user_instruction: str,
    edit_type: str,
    model_id: str = "qwen",
    wanx_size: str = "1024*1024",
    doubao_size: str = "2K",
) -> Tuple[str, str, str]:
    """Analyze uploaded image(s) with Vision LLM, then regenerate edited image.

    Returns `(image_url, display_prompt, provider_name)`.
    """
    vision_llm = model_registry.get_vision_client(temperature=0.3)

    content = [
        {
            "type": "text",
            "text": "请客观、详尽地描述这张图片中的主体人物/物体、姿势、服饰、场景、光线、构图和色彩细节。",
        }
    ]
    for img in images:
        content.append({"type": "image_url", "image_url": {"url": _normalize_data_url(img)}})

    vision_resp = await vision_llm.ainvoke([HumanMessage(content=content)])
    description = vision_resp.content if hasattr(vision_resp, "content") else str(vision_resp)

    edit_prompt, detail = _build_edit_prompt(description, edit_type, user_instruction)
    style = (
        "anime"
        if edit_type == "风格转换" and any(k in detail for k in ("漫画", "动漫", "卡通", "二次元"))
        else None
    )
    url, provider = await generate_image(
        prompt=edit_prompt,
        model_id=model_id,
        wanx_size=wanx_size,
        doubao_size=doubao_size,
        style=style,
    )
    return url, f"{edit_type}: {detail}", provider
