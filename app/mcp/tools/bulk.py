"""Bulk create tools: up to MAX_BULK_ITEMS items per call, saved all-or-nothing."""
from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.workspace import WorkspaceContext
from app.schemas.category import CategoryCreate
from app.schemas.transaction import TransactionCreate
from app.services.bulk import MAX_BULK_ITEMS
from app.services.category_service import create_categories_bulk
from app.services.transaction_service import create_transactions_bulk


class BulkEntriesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[TransactionCreate] = Field(min_length=1, max_length=MAX_BULK_ITEMS)


class BulkCategoriesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categories: list[CategoryCreate] = Field(min_length=1, max_length=MAX_BULK_ITEMS)


async def handle_create_transactions_bulk(
    db: AsyncSession, ctx: WorkspaceContext, transaction_type: str, arguments: dict
) -> object:
    args = BulkEntriesArgs(**arguments)
    created = await create_transactions_bulk(db, args.entries, transaction_type, ctx.business_id, ctx.user_id)
    return {"created": len(created), "items": jsonable_encoder(created)}


async def handle_create_categories_bulk(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    args = BulkCategoriesArgs(**arguments)
    created = await create_categories_bulk(db, args.categories, ctx.business_id, ctx.user_id)
    return {"created": len(created), "items": jsonable_encoder(created)}
