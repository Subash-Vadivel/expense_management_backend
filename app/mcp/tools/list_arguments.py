from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.category import CategoryType
from app.schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, MAX_SEARCH_LENGTH, SortOrder
from app.schemas.transaction import TransactionSortField


class ListArguments(BaseModel):
    """Validated list-tool arguments; a ValidationError surfaces to the client as INVALID_PARAMS."""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT)
    offset: int = Field(default=0, ge=0)
    search: str | None = Field(default=None, max_length=MAX_SEARCH_LENGTH)


class TransactionListArguments(ListArguments):
    startDate: date | None = None
    endDate: date | None = None
    sort: TransactionSortField = "date"
    order: SortOrder = "desc"


class CategoryListArguments(ListArguments):
    type: CategoryType
