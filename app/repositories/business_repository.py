from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.business import BusinessEntity, BusinessInvitation, BusinessMembership
from app.models.user import User


async def create_business(db: AsyncSession, business: BusinessEntity, membership: BusinessMembership) -> BusinessEntity:
    db.add(business)
    db.add(membership)
    await db.commit()
    await db.refresh(business)
    return business


async def get_business(db: AsyncSession, business_id: UUID) -> BusinessEntity | None:
    return await db.get(BusinessEntity, business_id)


async def get_membership(db: AsyncSession, business_id: UUID, user_id: UUID) -> BusinessMembership | None:
    result = await db.execute(
        select(BusinessMembership).where(
            BusinessMembership.business_id == business_id,
            BusinessMembership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_active_businesses_for_user(db: AsyncSession, user_id: UUID) -> list[tuple[BusinessEntity, BusinessMembership]]:
    result = await db.execute(
        select(BusinessEntity, BusinessMembership)
        .join(BusinessMembership, BusinessMembership.business_id == BusinessEntity.id)
        .where(BusinessMembership.user_id == user_id, BusinessMembership.status == "active")
        .order_by(BusinessEntity.created_at.asc())
    )
    return list(result.all())


async def count_active_members(db: AsyncSession, business_id: UUID) -> int:
    result = await db.execute(
        select(func.count(BusinessMembership.id)).where(
            BusinessMembership.business_id == business_id,
            BusinessMembership.status == "active",
        )
    )
    return int(result.scalar_one() or 0)


async def list_members(db: AsyncSession, business_id: UUID) -> list[tuple[BusinessMembership, User]]:
    result = await db.execute(
        select(BusinessMembership, User)
        .join(User, User.id == BusinessMembership.user_id)
        .where(BusinessMembership.business_id == business_id, BusinessMembership.status == "active")
        .order_by(BusinessMembership.created_at.asc())
    )
    return list(result.all())


async def create_invitation(db: AsyncSession, invitation: BusinessInvitation) -> BusinessInvitation:
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def find_invitation_by_token_hash(db: AsyncSession, token_hash: str) -> BusinessInvitation | None:
    result = await db.execute(select(BusinessInvitation).where(BusinessInvitation.token_hash == token_hash))
    return result.scalar_one_or_none()


async def list_invitations(db: AsyncSession, business_id: UUID) -> list[BusinessInvitation]:
    result = await db.execute(
        select(BusinessInvitation)
        .where(BusinessInvitation.business_id == business_id)
        .order_by(BusinessInvitation.created_at.desc())
    )
    return list(result.scalars().all())


async def find_pending_invitation_for_email(
    db: AsyncSession,
    business_id: UUID,
    email: str,
) -> BusinessInvitation | None:
    result = await db.execute(
        select(BusinessInvitation).where(
            BusinessInvitation.business_id == business_id,
            BusinessInvitation.email == email,
            BusinessInvitation.status == "pending",
        )
    )
    return result.scalar_one_or_none()


async def upsert_membership(db: AsyncSession, membership: BusinessMembership) -> BusinessMembership:
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


async def update_invitation(db: AsyncSession, invitation: BusinessInvitation) -> None:
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
