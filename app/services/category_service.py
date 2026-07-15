from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, CategoryType, CustomFieldDefinition
from app.models.common import parse_uuid
from app.repositories import category_repository
from app.schemas.category import CategoryCreate, CategoryResponse, CustomFieldCreate, CustomFieldResponse


def normalize_category_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def category_to_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=str(category.id),
        name=category.name,
        type=category.type,
        customFields=[
            CustomFieldResponse(
                id=field["id"],
                name=field["name"],
                type=field["type"],
                required=field.get("required", False),
            )
            for field in category.custom_fields
        ],
        createdBy=str(category.created_by),
        createdAt=category.created_at,
    )


def normalize_custom_field_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def build_custom_field_definitions(fields: list[CustomFieldCreate]) -> list[dict]:
    seen_names: set[str] = set()
    definitions: list[dict] = []
    for field in fields:
        normalized_name = normalize_custom_field_name(field.name)
        if normalized_name in seen_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom field names must be unique within a category",
            )
        seen_names.add(normalized_name)
        definition = CustomFieldDefinition(
            id=f"cf_{uuid4().hex}",
            name=" ".join(field.name.strip().split()),
            type=field.type,
            required=field.required,
        )
        definitions.append(definition.model_dump())
    return definitions


async def create_category(
    db: AsyncSession, payload: CategoryCreate, user_id: UUID
) -> CategoryResponse:
    normalized_name = normalize_category_name(payload.name)
    existing = await category_repository.find_category_by_normalized_name(
        db, user_id, payload.type, normalized_name
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists for this type",
        )

    category = Category(
        name=" ".join(payload.name.strip().split()),
        normalized_name=normalized_name,
        type=payload.type,
        custom_fields=build_custom_field_definitions(payload.customFields),
        created_by=user_id,
    )
    try:
        category_id = await category_repository.create_category(db, category)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists for this type",
        ) from exc
    created = await category_repository.find_category_by_id(db, category_id)
    return category_to_response(created)


async def list_categories(
    db: AsyncSession, category_type: CategoryType, user_id: UUID
) -> list[CategoryResponse]:
    categories = await category_repository.list_categories(db, category_type, user_id)
    return [category_to_response(category) for category in categories]


async def get_category_for_user(
    db: AsyncSession, category_id: str, category_type: CategoryType, user_id: UUID
) -> Category:
    category = await category_repository.find_category_for_user(
        db, parse_uuid(category_id, "category id"), category_type, user_id
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category
