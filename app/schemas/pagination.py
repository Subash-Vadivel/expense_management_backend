from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 200
MAX_SEARCH_LENGTH = 100

SortOrder = Literal["asc", "desc"]

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    hasMore: bool
    nextOffset: int | None = None

    @classmethod
    def page_fields(cls, total: int, limit: int, offset: int) -> dict:
        has_more = offset + limit < total
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "hasMore": has_more,
            "nextOffset": offset + limit if has_more else None,
        }


# "!" rather than backslash, so escaping doesn't depend on the database's string-literal settings.
LIKE_ESCAPE = "!"


def like_pattern(search: str) -> str:
    escaped = search.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escaped}%"


def clean_search(search: str | None) -> str | None:
    if search is None:
        return None
    search = " ".join(search.split())[:MAX_SEARCH_LENGTH]
    return search or None
