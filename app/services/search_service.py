"""Async Tavily web search wrapper with structured citation formatting."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

NEWS_KEYWORDS = ("新闻", "最新", "热点", "热搜", "事件", "发生了什么", "发布会")
TIME_SENSITIVE_KEYWORDS = ("今天", "今日", "昨天", "明天", "本周", "现在", "几号", "日期", "天气", "气温", "温度")


def _run_tavily_sync(query: str, api_key: str, max_results: int) -> List[Dict[str, Any]]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    is_news = any(k in query for k in NEWS_KEYWORDS)
    is_realtime = any(k in query for k in TIME_SENSITIVE_KEYWORDS)

    params: Dict[str, Any] = {
        "query": query,
        "max_results": max_results,
        "topic": "news" if is_news else "general",
        "search_depth": "advanced",
    }
    if is_realtime:
        params["time_range"] = "day"
    elif is_news:
        params["time_range"] = "week"

    try:
        response = client.search(**params)
    except TypeError:
        response = client.search(query=query, max_results=max_results)

    raw_results = response.get("results", []) if isinstance(response, dict) else []
    cleaned: List[Dict[str, Any]] = []
    for item in raw_results:
        cleaned.append(
            {
                "title": item.get("title") or "无标题",
                "url": item.get("url") or "",
                "content": (item.get("content") or "").strip(),
                "published_date": item.get("published_date") or "",
            }
        )
    return cleaned


async def search_web(query: str, max_results: int | None = None) -> List[Dict[str, Any]]:
    """Run Tavily web search off the event loop and return structured citations."""
    settings = get_settings()
    if not settings.tavily_api_key:
        return []

    limit = max_results or settings.tavily_max_results
    try:
        results = await asyncio.to_thread(
            _run_tavily_sync, query, settings.tavily_api_key, limit
        )
        logger.info("Web search completed query_len=%d results=%d", len(query), len(results))
        return results
    except Exception as exc:
        logger.warning("Web search failed: %s", exc)
        return []


def format_search_context(results: List[Dict[str, Any]]) -> str:
    """Format search citations into a concise reference block for LLM grounding."""
    if not results:
        return ""

    lines = ["以下是来自互联网的实时搜索结果，请优先结合这些信息回答，并在适当位置标注来源编号（如 [1]）："]
    for idx, item in enumerate(results, start=1):
        entry = [f"[{idx}] {item['title']}"]
        if item.get("published_date"):
            entry.append(f"发布时间: {item['published_date']}")
        if item.get("content"):
            entry.append(item["content"][:600])
        if item.get("url"):
            entry.append(f"链接: {item['url']}")
        lines.append("\n".join(entry))
    return "\n\n".join(lines)
