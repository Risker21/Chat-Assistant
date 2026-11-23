"""Persona listing and custom persona CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import Identity, get_current_identity
from app.db.database import get_db
from app.schemas.persona import PersonaCreate, PersonaResponse, PersonaUpdate
from app.services import persona_service

router = APIRouter(prefix="/api/v1/personas", tags=["Personas"])


@router.get("")
def list_personas(
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    items = persona_service.list_personas(db, identity.owner_key)
    return {"personas": [item.model_dump() for item in items]}


@router.post("", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
def create_persona(
    payload: PersonaCreate,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    return persona_service.create_persona(db, identity.owner_key, payload)


@router.put("/{persona_id}", response_model=PersonaResponse)
def update_persona(
    persona_id: str,
    payload: PersonaUpdate,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    if persona_id in persona_service.BUILTIN_PERSONAS:
        raise HTTPException(status_code=400, detail="内置角色不可修改，请创建一个新的自定义角色")
    updated = persona_service.update_persona(db, identity.owner_key, persona_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="角色不存在或无权修改")
    return updated


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(
    persona_id: str,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    if persona_id in persona_service.BUILTIN_PERSONAS:
        raise HTTPException(status_code=400, detail="内置角色不可删除")
    deleted = persona_service.delete_persona(db, identity.owner_key, persona_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="角色不存在或无权删除")
    return None
