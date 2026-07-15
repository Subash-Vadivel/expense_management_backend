from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.category import CategoryCreate
from app.services.category_service import create_category, list_categories
from app.services.mcp_api_key_service import McpApiKeyAuth


async def handle_list_categories(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    category_type = arguments["type"]
    return jsonable_encoder(await list_categories(db, category_type, auth.business_id))


async def handle_create_category(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    payload = CategoryCreate(**arguments)
    return jsonable_encoder(await create_category(db, payload, auth.business_id, auth.user_id))
