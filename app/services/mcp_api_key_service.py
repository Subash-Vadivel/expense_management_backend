from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.mcp_api_key import McpApiKeyModel
from app.repositories import mcp_api_key_repository
from app.schemas.mcp_api_key import McpApiKeyCreate, McpApiKeyCreateResponse, McpApiKeyResponse

KEY_PREFIX = "farm_mcp_"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"


def api_key_to_response(api_key: dict) -> McpApiKeyResponse:
    return McpApiKeyResponse(
        id=str(api_key["_id"]),
        name=api_key["name"],
        keyPrefix=api_key["keyPrefix"],
        enabled=api_key["enabled"],
        createdAt=api_key["createdAt"],
        lastUsedAt=api_key.get("lastUsedAt"),
        disabledAt=api_key.get("disabledAt"),
    )


async def create_api_key(
    db: AsyncIOMotorDatabase,
    payload: McpApiKeyCreate,
    user_id: ObjectId,
) -> McpApiKeyCreateResponse:
    raw_key = generate_api_key()
    key_prefix = raw_key[:18]
    api_key = McpApiKeyModel(
        name=" ".join(payload.name.strip().split()),
        keyHash=hash_api_key(raw_key),
        keyPrefix=key_prefix,
        createdBy=user_id,
    )
    api_key_id = await mcp_api_key_repository.create_api_key(db, api_key.to_mongo())
    created = await mcp_api_key_repository.find_api_key_by_id(db, api_key_id)
    return McpApiKeyCreateResponse(**api_key_to_response(created).model_dump(), apiKey=raw_key)


async def list_api_keys(db: AsyncIOMotorDatabase, user_id: ObjectId) -> list[McpApiKeyResponse]:
    api_keys = await mcp_api_key_repository.list_api_keys_for_user(db, user_id)
    return [api_key_to_response(api_key) for api_key in api_keys]


async def set_api_key_enabled(
    db: AsyncIOMotorDatabase,
    api_key_id: str,
    user_id: ObjectId,
    enabled: bool,
) -> McpApiKeyResponse:
    if not ObjectId.is_valid(api_key_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid API key id")
    existing = await mcp_api_key_repository.find_api_key_for_user(db, ObjectId(api_key_id), user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    update_data = {"enabled": enabled}
    update_data["disabledAt"] = None if enabled else datetime.now(timezone.utc)
    await mcp_api_key_repository.update_api_key(db, existing["_id"], update_data)
    updated = await mcp_api_key_repository.find_api_key_by_id(db, existing["_id"])
    return api_key_to_response(updated)


async def delete_api_key(db: AsyncIOMotorDatabase, api_key_id: str, user_id: ObjectId) -> None:
    if not ObjectId.is_valid(api_key_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid API key id")
    result = await mcp_api_key_repository.delete_api_key(db, ObjectId(api_key_id), user_id)
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")


async def authenticate_api_key(db: AsyncIOMotorDatabase, raw_key: str) -> ObjectId | None:
    if not raw_key.startswith(KEY_PREFIX):
        return None
    api_key = await mcp_api_key_repository.find_api_key_by_hash(db, hash_api_key(raw_key))
    if not api_key or not api_key.get("enabled", False):
        return None
    await mcp_api_key_repository.update_api_key(
        db, api_key["_id"], {"lastUsedAt": datetime.now(timezone.utc)}
    )
    return api_key["createdBy"]
