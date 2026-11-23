"""FastAPI dependencies for database sessions and user/guest identity resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.db.models import User

GUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


@dataclass
class Identity:
    owner_key: str
    is_guest: bool
    user: Optional[User] = None
    guest_id: Optional[str] = None


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def _sanitize_guest_id(raw_guest_id: Optional[str]) -> str:
    if raw_guest_id and GUEST_ID_PATTERN.match(raw_guest_id.strip()):
        return raw_guest_id.strip()
    return "anonymous-default"


def get_current_identity(
    authorization: Optional[str] = Header(default=None),
    x_guest_id: Optional[str] = Header(default=None, alias="X-Guest-ID"),
    db: Session = Depends(get_db),
) -> Identity:
    """Resolve authenticated User from Bearer JWT, or seamlessly fall back to Guest identity."""
    token = _extract_bearer_token(authorization)
    if token:
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            user = db.query(User).filter(User.id == payload["sub"]).first()
            if user:
                return Identity(
                    owner_key=user.owner_key,
                    is_guest=False,
                    user=user,
                    guest_id=x_guest_id.strip() if x_guest_id else None,
                )

    guest_id = _sanitize_guest_id(x_guest_id)
    return Identity(
        owner_key=f"guest:{guest_id}",
        is_guest=True,
        user=None,
        guest_id=guest_id,
    )


def require_authenticated_user(
    identity: Identity = Depends(get_current_identity),
) -> User:
    """Require a logged-in User account."""
    if identity.is_guest or identity.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录账号后再执行此操作",
        )
    return identity.user
