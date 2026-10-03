from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, CategoryType, CustomFieldDefinition
from app.models.common import parse_uuid
from app.repositories import category_repository
from app.schemas.category import CategoryCreate, CategoryPage, CategoryResponse, CustomFieldCreate, CustomFieldResponse
from app.schemas.pagination import DEFAULT_PAGE_LIMIT, clean_search
from app.services.bulk import bulk_rejected, item_error_message


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


async def create_categories_bulk(
    db: AsyncSession,
    payloads: list[CategoryCreate],
    business_id: UUID,
    user_id: UUID,
) -> list[CategoryResponse]:
    """Create up to MAX_BULK_ITEMS categories in one transaction: all are saved, or none if any is invalid."""
    built: list[Category] = []
    errors: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for index, payload in enumerate(payloads):
        key = (payload.type, normalize_category_name(payload.name))
        if key in seen:
            errors.append({"index": index, "error": f"Duplicate of an earlier {payload.type} category in this batch"})
            continue
        seen.add(key)
        try:
            if await category_repository.find_category_by_normalized_name(db, business_id, payload.type, key[1]):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists for this type")
            built.append(build_category(payload, business_id, user_id))
        except HTTPException as exc:
            errors.append({"index": index, "error": item_error_message(exc)})
    if errors:
        raise bulk_rejected(errors)
    db.add_all(built)
    try:
        await db.commit()
    except IntegrityError as exc:
        # A category with one of these names was created between the check and the save.
        await db.rollback()
        raise bulk_rejected([{"index": None, "error": "A category in this batch already exists for its type"}]) from exc
    for category in built:
        await db.refresh(category)
    return [category_to_response(category) for category in built]


def build_category(payload: CategoryCreate, business_id: UUID, user_id: UUID) -> Category:
    return Category(
        name=" ".join(payload.name.strip().split()),
        normalized_name=normalize_category_name(payload.name),
        type=payload.type,
        custom_fields=build_custom_field_definitions(payload.customFields),
        business_id=business_id,
        created_by=user_id,
    )


async def create_category(
    db: AsyncSession,
    payload: CategoryCreate,
    business_id: UUID,
    user_id: UUID,
) -> CategoryResponse:
    normalized_name = normalize_category_name(payload.name)
    existing = await category_repository.find_category_by_normalized_name(
        db, business_id, payload.type, normalized_name
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists for this type",
        )

    category = build_category(payload, business_id, user_id)
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
    db: AsyncSession,
    category_type: CategoryType,
    business_id: UUID,
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
    search: str | None = None,
) -> CategoryPage:
    filters = category_repository.list_filters(category_type, business_id, clean_search(search))
    categories = await category_repository.list_categories(db, filters, limit, offset)
    total = await category_repository.count_categories(db, filters)
    return CategoryPage(
        items=[category_to_response(category) for category in categories],
        **CategoryPage.page_fields(total, limit, offset),
    )


async def get_category_for_business(
    db: AsyncSession, category_id: str, category_type: CategoryType, business_id: UUID
) -> Category:
    category = await category_repository.find_category_for_business(
        db, parse_uuid(category_id, "category id"), category_type, business_id
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


def category_in_use() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "category_in_use",
            "message": "Records already exist for this category, so it can't be deleted.",
        },
    )


async def delete_category(db: AsyncSession, category_id: str, business_id: UUID) -> None:
    category = await category_repository.find_category_in_business(
        db, parse_uuid(category_id, "category id"), business_id
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if await category_repository.category_has_transactions(db, category.id):
        raise category_in_use()
    try:
        await category_repository.delete_category(db, category)
    except IntegrityError as exc:
        # An entry was added between the check and the delete; the FK (ON DELETE RESTRICT) caught it.
        await db.rollback()
        raise category_in_use() from exc
