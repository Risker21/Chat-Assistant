"""Chat streaming (SSE), non-streaming chat, image generation, and legacy endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import Identity, get_current_identity
from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ImageGenerateRequest, ImageGenerateResponse
from app.services.chat_service import complete_chat, format_sse, stream_chat_events
from app.services.image_service import generate_image
from app.services.intent_service import parse_image_size
from app.services.model_registry import ModelError

router = APIRouter(tags=["Chat"])


@router.post("/api/v1/chat/stream")
async def chat_stream_v1(
    payload: ChatRequest,
    request: Request,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Real-time Server-Sent Events streaming chat endpoint with DB persistence."""

    async def event_generator():
        async for event_name, data in stream_chat_events(
            db=db,
            owner_key=identity.owner_key,
            req=payload,
            http_request=request,
            persist=True,
        ):
            yield format_sse(event_name, data)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat_v1(
    payload: ChatRequest,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Standard non-streaming chat endpoint with DB persistence."""
    return await complete_chat(db=db, owner_key=identity.owner_key, req=payload, persist=True)


@router.post("/api/v1/images/generate", response_model=ImageGenerateResponse)
async def generate_image_v1(payload: ImageGenerateRequest):
    """Dedicated text-to-image generation endpoint."""
    wanx_size, doubao_size = parse_image_size(payload.size)
    try:
        image_url, provider = await generate_image(
            prompt=payload.prompt,
            model_id=payload.model,
            wanx_size=wanx_size,
            doubao_size=doubao_size,
        )
        return ImageGenerateResponse(
            image_url=image_url,
            prompt=payload.prompt,
            provider=provider,
        )
    except ModelError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/chat", response_model=ChatResponse)
async def chat_legacy(
    payload: ChatRequest,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Backward-compatible stateless/stateful chat endpoint for legacy API callers."""
    persist = bool(payload.conversation_id)
    return await complete_chat(db=db, owner_key=identity.owner_key, req=payload, persist=persist)


@router.post("/generate_image")
async def generate_image_legacy(payload: ImageGenerateRequest):
    """Backward-compatible image generation endpoint."""
    wanx_size, doubao_size = parse_image_size(payload.size)
    try:
        image_url, provider = await generate_image(
            prompt=payload.prompt,
            model_id=payload.model,
            wanx_size=wanx_size,
            doubao_size=doubao_size,
        )
        return {"image_url": image_url, "provider": provider}
    except ModelError as exc:
        return {"error": exc.message}
