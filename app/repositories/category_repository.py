from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.category import Category, CategoryType


async def find_category_by_normalized_name(
    db: AsyncSession,
    business_id: UUID,
    category_type: CategoryType,
    normalized_name: str,
) -> Category | None:
    result = await db.execute(
        select(Category).where(
            Category.business_id == business_id,
            Category.type == category_type,
            Category.normalized_name == normalized_name,
        )
    )
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, category: Category) -> UUID:
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category.id


async def find_category_by_id(db: AsyncSession, category_id: UUID) -> Category | None:
    return await db.get(Category, category_id)


async def find_category_for_business(
    db: AsyncSession,
    category_id: UUID,
    category_type: CategoryType,
    business_id: UUID,
) -> Category | None:
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.business_id == business_id,
            Category.type == category_type,
        )
    )
    return result.scalar_one_or_none()


async def list_categories(
    db: AsyncSession,
    category_type: CategoryType,
    business_id: UUID,
) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.business_id == business_id, Category.type == category_type)
        .order_by(Category.name.asc())
    )
    return list(result.scalars().all())
