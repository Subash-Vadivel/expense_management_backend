from __future__ import annotations

from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.models.category import CategoryModel, CategoryType, CustomFieldDefinition
from app.schemas.category import CategoryCreate, CategoryResponse, CustomFieldCreate, CustomFieldResponse


def normalize_category_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def category_to_response(category: dict) -> CategoryResponse:
    return CategoryResponse(
        id=str(category["_id"]),
        name=category["name"],
        type=category["type"],
        customFields=[
            CustomFieldResponse(
                id=field["id"],
                name=field["name"],
                type=field["type"],
                required=field.get("required", False),
            )
            for field in category.get("customFields", [])
        ],
        createdBy=str(category["createdBy"]),
        createdAt=category["createdAt"],
    )


def user_ownership_filter(user_id: ObjectId) -> dict:
    return {"$in": [user_id, str(user_id)]}


def normalize_custom_field_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def build_custom_field_definitions(fields: list[CustomFieldCreate]) -> list[CustomFieldDefinition]:
    seen_names: set[str] = set()
    definitions: list[CustomFieldDefinition] = []
    for field in fields:
        normalized_name = normalize_custom_field_name(field.name)
        if normalized_name in seen_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom field names must be unique within a category",
            )
        seen_names.add(normalized_name)
        definitions.append(
            CustomFieldDefinition(
                id=f"cf_{uuid4().hex}",
                name=" ".join(field.name.strip().split()),
                type=field.type,
                required=field.required,
            )
        )
    return definitions


async def create_category(
    db: AsyncIOMotorDatabase, payload: CategoryCreate, user_id: ObjectId
) -> CategoryResponse:
    normalized_name = normalize_category_name(payload.name)
    existing = await db.categories.find_one(
        {
            "createdBy": user_ownership_filter(user_id),
            "type": payload.type,
            "normalizedName": normalized_name,
        }
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists for this type",
        )

    category = CategoryModel(
        name=" ".join(payload.name.strip().split()),
        normalizedName=normalized_name,
        type=payload.type,
        customFields=build_custom_field_definitions(payload.customFields),
        createdBy=user_id,
    )
    try:
        result = await db.categories.insert_one(category.to_mongo())
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists for this type",
        ) from exc
    created = await db.categories.find_one({"_id": result.inserted_id})
    return category_to_response(created)


async def list_categories(
    db: AsyncIOMotorDatabase, category_type: CategoryType, user_id: ObjectId
) -> list[CategoryResponse]:
    cursor = db.categories.find(
        {"createdBy": user_ownership_filter(user_id), "type": category_type}
    ).sort("name", 1)
    return [category_to_response(category) async for category in cursor]


async def get_category_for_user(
    db: AsyncIOMotorDatabase, category_id: str, category_type: CategoryType, user_id: ObjectId
) -> dict:
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category id")
    category = await db.categories.find_one(
        {
            "_id": ObjectId(category_id),
            "createdBy": user_ownership_filter(user_id),
            "type": category_type,
        }
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category
