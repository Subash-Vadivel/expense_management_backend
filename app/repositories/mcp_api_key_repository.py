from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.mcp_api_key import McpApiKey


async def create_api_key(db: AsyncSession, api_key: McpApiKey) -> UUID:
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key.id


async def find_api_key_by_id(db: AsyncSession, api_key_id: UUID) -> McpApiKey | None:
    return await db.get(McpApiKey, api_key_id)


async def find_api_key_for_user(
    db: AsyncSession,
    api_key_id: UUID,
    user_id: UUID,
) -> McpApiKey | None:
    result = await db.execute(
        select(McpApiKey).where(McpApiKey.id == api_key_id, McpApiKey.created_by == user_id)
    )
    return result.scalar_one_or_none()


async def find_api_key_by_hash(db: AsyncSession, key_hash: str) -> McpApiKey | None:
    result = await db.execute(select(McpApiKey).where(McpApiKey.key_hash == key_hash))
    return result.scalar_one_or_none()


async def list_api_keys_for_user(db: AsyncSession, user_id: UUID) -> list[McpApiKey]:
    result = await db.execute(
        select(McpApiKey)
        .where(McpApiKey.created_by == user_id)
        .order_by(McpApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def update_api_key(db: AsyncSession, api_key: McpApiKey) -> None:
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)


async def delete_api_key(
    db: AsyncSession,
    api_key_id: UUID,
    user_id: UUID,
) -> int:
    result = await db.execute(
        delete(McpApiKey).where(McpApiKey.id == api_key_id, McpApiKey.created_by == user_id)
    )
    await db.commit()
    return result.rowcount or 0
