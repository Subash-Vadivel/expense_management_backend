from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.category import Category, CategoryType
from app.models.transaction import Transaction
from app.schemas.pagination import LIKE_ESCAPE, like_pattern


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


def list_filters(category_type: CategoryType, business_id: UUID, search: str | None = None) -> list:
    filters = [Category.business_id == business_id, Category.type == category_type]
    if search:
        filters.append(Category.name.ilike(like_pattern(search), escape=LIKE_ESCAPE))
    return filters


async def list_categories(db: AsyncSession, filters: list, limit: int = 50, offset: int = 0) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(*filters)
        .order_by(Category.name.asc(), Category.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def count_categories(db: AsyncSession, filters: list) -> int:
    result = await db.execute(select(func.count(Category.id)).where(*filters))
    return int(result.scalar_one())


async def find_category_in_business(db: AsyncSession, category_id: UUID, business_id: UUID) -> Category | None:
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.business_id == business_id)
    )
    return result.scalar_one_or_none()


async def category_has_transactions(db: AsyncSession, category_id: UUID) -> bool:
    result = await db.execute(select(exists().where(Transaction.category_id == category_id)))
    return bool(result.scalar())


async def delete_category(db: AsyncSession, category: Category) -> None:
    await db.delete(category)
    await db.commit()
