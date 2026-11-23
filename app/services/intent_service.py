"""Accurate user intent routing for chat, web search, vision, and image generation/editing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

IntentKind = Literal["chat", "web_search", "vision_chat", "image_generate", "image_edit"]

# Phrases that explicitly indicate non-image generation (e.g., code, text, SQL, tables)
NON_IMAGE_GEN_PATTERN = re.compile(
    r"(生成|写|创建)(一段|一份|一个|一篇|一些)?\s*"
    r"(代码|脚本|函数|程序|文章|文案|总结|摘要|报告|表格|SQL|JSON|YAML|HTML|CSS|Python|Java|JS|简历|大纲|标题|邮件|方案|测试用例|提示词|prompt)",
    re.IGNORECASE,
)

# Clear image generation intents
IMAGE_GEN_PATTERNS = [
    re.compile(r"(帮我|给我|请)?(画|绘制|绘出|生成)(一张|一幅|一个|张|幅|个)?.*?(图|画|插画|照片|头像|海报|壁纸|封面|logo|风景|人物|猫咪|女孩|男孩|场景|漫画|油画|水彩|素描)", re.IGNORECASE),
    re.compile(r"^(画一个|画一张|画一幅|画个|帮我画|给我画|来一张图|来张图|来个图|生成图片|生成一张图|画画[:：]?)", re.IGNORECASE),
    re.compile(r"\b(generate|create|draw|paint)\s+(an?\s+)?(image|picture|photo|illustration|artwork|wallpaper|logo)\b", re.IGNORECASE),
]

EDIT_KEYWORDS: dict[str, list[str]] = {
    "风格转换": ["转换成", "转成", "变成", "改为", "风格化", "动漫风", "漫画风", "卡通风", "油画风", "水彩风", "素描风", "像素风", "赛博朋克风"],
    "背景替换": ["换背景", "背景换", "背景替换", "更换背景", "背景改成", "背景变为", "背景换成", "换成背景", "抠图换背景"],
    "调整优化": ["提亮", "变暗", "调亮", "调暗", "调色", "对比度", "清晰度", "去模糊", "超分", "修图"],
    "添加元素": ["图片中添加", "图中添加", "加上一个", "放入一个", "P上", "p上"],
    "移除元素": ["移除背景", "删除背景", "去掉背景", "擦除", "消除水印", "去水印", "P掉", "p掉"],
    "滤镜效果": ["加滤镜", "滤镜效果", "黑白滤镜", "复古滤镜", "胶片感"],
}

EXPLICIT_SEARCH_PATTERNS = [
    re.compile(r"(帮我|请)?(搜索|搜一下|查一下|查询|联网搜索|网上查|查找一下)", re.IGNORECASE),
    re.compile(r"\b(web\s*search|search\s+for|look\s+up|latest\s+news)\b", re.IGNORECASE),
]

REALTIME_SEARCH_PATTERNS = [
    re.compile(r"(今天|今日|明天|现在|当前|实时|最新|最近).*(天气|气温|温度|新闻|消息|股价|汇率|比分|价格|政策|发布会|行情|热搜)", re.IGNORECASE),
    re.compile(r"(天气|气温|温度)(怎么样|如何|预报|多少度)", re.IGNORECASE),
    re.compile(r"(今天|现在)(是)?(几号|星期几|周几|几点|什么日期)", re.IGNORECASE),
    re.compile(r"(202[5-9]|203\d)年.*(最新|发布|冠军|排名|价格|消息)"),
]

SIZE_PATTERN = re.compile(
    r"(\d{3,4}\s*[x×*]\s*\d{3,4}|\d{3,4}px|2K|4K|8K|高清|超清|竖版|横版|方图)",
    re.IGNORECASE,
)


@dataclass
class DetectedIntent:
    kind: IntentKind
    image_size: str = "1024*1024"
    doubao_size: str = "2K"
    edit_type: Optional[str] = None
    reason: str = ""


def parse_image_size(message: str) -> tuple[str, str]:
    """Extract normalized (wanx_size, doubao_size) from user message."""
    match = SIZE_PATTERN.search(message or "")
    if not match:
        return "1024*1024", "2K"

    token = match.group(1).strip().upper()
    if token in ("4K", "8K", "超清"):
        return "1024*1024", "4K"
    if token in ("2K", "高清", "方图"):
        return "1024*1024", "2K"
    if token == "横版":
        return "1280*720", "2K"
    if token == "竖版":
        return "720*1280", "2K"

    dim_match = re.match(r"(\d{3,4})\s*[X×*]\s*(\d{3,4})", token)
    if dim_match:
        w, h = int(dim_match.group(1)), int(dim_match.group(2))
        w = max(512, min(2048, w))
        h = max(512, min(2048, h))
        return f"{w}*{h}", f"{w}x{h}"

    px_match = re.match(r"(\d{3,4})PX", token)
    if px_match:
        s = max(512, min(2048, int(px_match.group(1))))
        return f"{s}*{s}", f"{s}x{s}"

    return "1024*1024", "2K"


def detect_edit_type(message: str) -> Optional[str]:
    for edit_type, keywords in EDIT_KEYWORDS.items():
        if any(kw in message for kw in keywords):
            return edit_type
    return None


def detect_intent(
    message: str,
    has_images: bool = False,
    web_search_mode: Literal["auto", "on", "off"] = "auto",
    image_mode: Literal["auto", "generate", "edit", "off"] = "auto",
) -> DetectedIntent:
    """Determine the execution route based on explicit user toggles and message content."""
    text = (message or "").strip()
    wanx_size, doubao_size = parse_image_size(text)

    # 1. Explicit image toggles take top priority
    if image_mode == "edit" and has_images:
        return DetectedIntent(
            kind="image_edit",
            image_size=wanx_size,
            doubao_size=doubao_size,
            edit_type=detect_edit_type(text) or "图片编辑",
            reason="explicit_image_edit",
        )
    if image_mode == "generate":
        return DetectedIntent(
            kind="image_generate",
            image_size=wanx_size,
            doubao_size=doubao_size,
            reason="explicit_image_generate",
        )

    # 2. If user uploaded images
    if has_images:
        if image_mode == "auto":
            edit_type = detect_edit_type(text)
            if edit_type:
                return DetectedIntent(
                    kind="image_edit",
                    image_size=wanx_size,
                    doubao_size=doubao_size,
                    edit_type=edit_type,
                    reason=f"detected_edit:{edit_type}",
                )
        return DetectedIntent(kind="vision_chat", reason="has_uploaded_images")

    # 3. Explicit web search toggle
    if web_search_mode == "on":
        return DetectedIntent(kind="web_search", reason="explicit_web_search")

    # 4. Auto image generation detection (guarded against "生成代码", "生成文章", etc.)
    if image_mode == "auto" and text and not NON_IMAGE_GEN_PATTERN.search(text):
        for pattern in IMAGE_GEN_PATTERNS:
            if pattern.search(text):
                return DetectedIntent(
                    kind="image_generate",
                    image_size=wanx_size,
                    doubao_size=doubao_size,
                    reason="detected_image_generate",
                )

    # 5. Auto web search detection (only genuine search / realtime queries)
    if web_search_mode == "auto" and text:
        for pattern in EXPLICIT_SEARCH_PATTERNS:
            if pattern.search(text):
                return DetectedIntent(kind="web_search", reason="explicit_search_phrase")
        for pattern in REALTIME_SEARCH_PATTERNS:
            if pattern.search(text):
                return DetectedIntent(kind="web_search", reason="realtime_info_query")

    return DetectedIntent(kind="chat", reason="default_chat")
