from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user_token import UserToken


async def create_token(db: AsyncSession, token: UserToken) -> UserToken:
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def find_valid_token(db: AsyncSession, token_hash: str, purpose: str) -> UserToken | None:
    result = await db.execute(
        select(UserToken).where(
            UserToken.token_hash == token_hash,
            UserToken.purpose == purpose,
            UserToken.used_at.is_(None),
            UserToken.expires_at > datetime.utcnow(),
        )
    )
    return result.scalar_one_or_none()


async def invalidate_tokens_for_user(db: AsyncSession, user_id: UUID, purpose: str) -> None:
    """Mark every unused token of this purpose as used. Does not commit."""
    await db.execute(
        update(UserToken)
        .where(UserToken.user_id == user_id, UserToken.purpose == purpose, UserToken.used_at.is_(None))
        .values(used_at=datetime.utcnow())
    )
