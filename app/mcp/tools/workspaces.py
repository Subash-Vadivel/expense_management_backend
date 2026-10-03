"""Account-level MCP tools: they act on the key's user, not on one workspace."""
from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.business import BusinessCreate
from app.services.business_service import create_business, list_businesses
from app.services.mcp_api_key_service import McpApiKeyAuth


def workspace_summary(business) -> dict:
    return {"id": business.id, "name": business.name, "legalName": business.legalName, "role": business.role}


async def handle_list_workspaces(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    businesses = await list_businesses(db, auth.user_id)
    return {"workspaces": [workspace_summary(b) for b in businesses]}


async def handle_create_workspace(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    business = await create_business(db, BusinessCreate(**arguments), auth.user_id)
    return jsonable_encoder(workspace_summary(business))
