from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.tools.list_arguments import CategoryListArguments
from app.schemas.category import CategoryCreate
from app.services.category_service import create_category, delete_category, list_categories
from app.mcp.workspace import WorkspaceContext


async def handle_list_categories(db: AsyncSession, auth: WorkspaceContext, arguments: dict) -> object:
    args = CategoryListArguments(**arguments)
    return jsonable_encoder(
        await list_categories(db, args.type, auth.business_id, args.limit, args.offset, args.search)
    )


async def handle_create_category(db: AsyncSession, auth: WorkspaceContext, arguments: dict) -> object:
    payload = CategoryCreate(**arguments)
    return jsonable_encoder(await create_category(db, payload, auth.business_id, auth.user_id))


async def handle_delete_category(db: AsyncSession, auth: WorkspaceContext, arguments: dict) -> object:
    category_id = arguments.get("categoryId")
    if not isinstance(category_id, str):
        raise ValueError("categoryId is required")
    await delete_category(db, category_id, auth.business_id)
    return {"deleted": True, "categoryId": category_id}
