"""Authentication routes with seamless guest-to-account data migration."""

from __future__ import annotations

from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import GUEST_ID_PATTERN, Identity, get_current_identity
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models import Conversation, Persona, User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserProfile

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _migrate_guest_data(db: Session, guest_id: Optional[str], user: User) -> Tuple[int, int]:
    """Transfer any guest conversations and custom personas to the authenticated user."""
    if not guest_id or not GUEST_ID_PATTERN.match(guest_id.strip()):
        return 0, 0
    guest_owner = f"guest:{guest_id.strip()}"

    conv_count = (
        db.query(Conversation)
        .filter(Conversation.owner_key == guest_owner)
        .update({Conversation.owner_key: user.owner_key}, synchronize_session=False)
    )
    persona_count = (
        db.query(Persona)
        .filter(Persona.owner_key == guest_owner)
        .update({Persona.owner_key: user.owner_key}, synchronize_session=False)
    )
    db.commit()
    return int(conv_count or 0), int(persona_count or 0)


def _to_profile(user: User) -> UserProfile:
    return UserProfile(
        id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
        email=user.email,
        is_guest=False,
        created_at=user.created_at,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    x_guest_id: Optional[str] = Header(default=None, alias="X-Guest-ID"),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="该用户名已被注册")

    if payload.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise HTTPException(status_code=409, detail="该邮箱已被注册")

    user = User(
        username=payload.username,
        email=payload.email,
        display_name=(payload.display_name or payload.username).strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    migrated_convs, migrated_personas = _migrate_guest_data(db, x_guest_id, user)
    token = create_access_token(subject=user.id, extra_claims={"username": user.username})

    return AuthResponse(
        access_token=token,
        user=_to_profile(user),
        migrated_conversations=migrated_convs,
        migrated_personas=migrated_personas,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    x_guest_id: Optional[str] = Header(default=None, alias="X-Guest-ID"),
    db: Session = Depends(get_db),
):
    identifier = payload.username.strip()
    user = (
        db.query(User)
        .filter((User.username == identifier) | (User.email == identifier.lower()))
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    migrated_convs, migrated_personas = _migrate_guest_data(db, x_guest_id, user)
    token = create_access_token(subject=user.id, extra_claims={"username": user.username})

    return AuthResponse(
        access_token=token,
        user=_to_profile(user),
        migrated_conversations=migrated_convs,
        migrated_personas=migrated_personas,
    )


@router.get("/me", response_model=UserProfile)
def get_me(identity: Identity = Depends(get_current_identity)):
    if not identity.is_guest and identity.user is not None:
        return _to_profile(identity.user)
    return UserProfile(
        id=identity.guest_id or "guest",
        username="guest",
        display_name="游客体验模式",
        is_guest=True,
    )
