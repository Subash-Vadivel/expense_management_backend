from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import BusinessAccess, require_business_role
from app.schemas.mcp_api_key import McpApiKeyCreate, McpApiKeyCreateResponse, McpApiKeyResponse, McpApiKeyUpdate
from app.services import mcp_api_key_service

router = APIRouter()


@router.post("/api-keys", response_model=McpApiKeyCreateResponse, status_code=201)
async def create_api_key(
    payload: McpApiKeyCreate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin")),
) -> McpApiKeyCreateResponse:
    return await mcp_api_key_service.create_api_key(db, payload, access.business.id, access.user.id)


@router.get("/api-keys", response_model=list[McpApiKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin")),
) -> list[McpApiKeyResponse]:
    return await mcp_api_key_service.list_api_keys(db, access.business.id)


@router.patch("/api-keys/{api_key_id}", response_model=McpApiKeyResponse)
async def update_api_key(
    api_key_id: str,
    payload: McpApiKeyUpdate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin")),
) -> McpApiKeyResponse:
    return await mcp_api_key_service.set_api_key_enabled(db, api_key_id, access.business.id, payload.enabled)


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_api_key(
    api_key_id: str,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin")),
) -> Response:
    await mcp_api_key_service.delete_api_key(db, api_key_id, access.business.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
