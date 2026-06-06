from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.dependencies.auth import get_current_user_id
from app.schemas.mcp_api_key import McpApiKeyCreate, McpApiKeyCreateResponse, McpApiKeyResponse, McpApiKeyUpdate
from app.services import mcp_api_key_service

router = APIRouter()


@router.post("/api-keys", response_model=McpApiKeyCreateResponse, status_code=201)
async def create_api_key(
    payload: McpApiKeyCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> McpApiKeyCreateResponse:
    return await mcp_api_key_service.create_api_key(db, payload, user_id)


@router.get("/api-keys", response_model=list[McpApiKeyResponse])
async def list_api_keys(
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> list[McpApiKeyResponse]:
    return await mcp_api_key_service.list_api_keys(db, user_id)


@router.patch("/api-keys/{api_key_id}", response_model=McpApiKeyResponse)
async def update_api_key(
    api_key_id: str,
    payload: McpApiKeyUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> McpApiKeyResponse:
    return await mcp_api_key_service.set_api_key_enabled(db, api_key_id, user_id, payload.enabled)


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_api_key(
    api_key_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> Response:
    await mcp_api_key_service.delete_api_key(db, api_key_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
