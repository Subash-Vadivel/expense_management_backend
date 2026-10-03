"""Workspace totals for a date range, so agents don't page through every entry to add them up."""
from __future__ import annotations

from datetime import date

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.workspace import WorkspaceContext
from app.services.dashboard_service import get_category_totals, get_summary

TOP_CATEGORIES = 5


class SummaryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    startDate: date | None = None
    endDate: date | None = None


async def handle_get_summary(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    args = SummaryArgs(**arguments)
    totals = await get_summary(db, ctx.business_id, args.startDate, args.endDate)
    income = await get_category_totals(db, ctx.business_id, "income", args.startDate, args.endDate)
    expense = await get_category_totals(db, ctx.business_id, "expense", args.startDate, args.endDate)
    return jsonable_encoder(
        {
            "range": {"startDate": args.startDate, "endDate": args.endDate},
            **totals.model_dump(),
            "topIncomeCategories": income[:TOP_CATEGORIES],
            "topExpenseCategories": expense[:TOP_CATEGORIES],
        }
    )
