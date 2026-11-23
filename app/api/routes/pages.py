"""Frontend entry page route."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(include_in_schema=False)

BASE_DIR = Path(__file__).resolve().parents[3]


@router.get("/")
async def index_page():
    return FileResponse(BASE_DIR / "static" / "index.html")
