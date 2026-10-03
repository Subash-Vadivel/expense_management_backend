from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, MAX_SEARCH_LENGTH
from app.mcp.tools.categories import handle_create_category, handle_list_categories
from app.services.business_service import WRITE_FINANCE_ROLES
from app.services.mcp_api_key_service import McpApiKeyAuth
from app.mcp.tools.transactions import (
    handle_create_transaction,
    handle_delete_transaction,
    handle_list_transactions,
    handle_update_transaction,
)

ToolHandler = Callable[[AsyncSession, McpApiKeyAuth, dict[str, Any]], Awaitable[object]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler
    # Write tools need a role in WRITE_FINANCE_ROLES, matching the REST routes.
    writes: bool = False

    def to_mcp(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


category_type_property = {"type": "string", "enum": ["income", "expense"]}
custom_fields_property = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "type": {"type": "string", "enum": ["STRING", "NUMBER", "BOOLEAN"]},
            "required": {"type": "boolean"},
        },
        "required": ["name", "type"],
    },
}
transaction_payload_properties = {
    "date": {"type": "string", "format": "date"},
    "categoryId": {"type": "string"},
    "description": {"type": ["string", "null"]},
    "amount": {"type": "number", "exclusiveMinimum": 0},
    "customFieldValues": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"fieldId": {"type": "string"}, "value": {}},
            "required": ["fieldId"],
        },
    },
}


pagination_properties = {
    "limit": {
        "type": "integer",
        "minimum": 1,
        "maximum": MAX_PAGE_LIMIT,
        "default": DEFAULT_PAGE_LIMIT,
        "description": f"Page size (1-{MAX_PAGE_LIMIT}, default {DEFAULT_PAGE_LIMIT}).",
    },
    "offset": {
        "type": "integer",
        "minimum": 0,
        "default": 0,
        "description": "Number of items to skip. Pass the previous response's nextOffset to get the next page.",
    },
}
transaction_list_properties = {
    "startDate": {"type": "string", "format": "date", "description": "Only entries on or after this date (YYYY-MM-DD)."},
    "endDate": {"type": "string", "format": "date", "description": "Only entries on or before this date (YYYY-MM-DD)."},
    "search": {
        "type": "string",
        "maxLength": MAX_SEARCH_LENGTH,
        "description": "Case-insensitive match on description or category name.",
    },
    "sort": {"type": "string", "enum": ["date", "amount", "category"], "default": "date"},
    "order": {"type": "string", "enum": ["asc", "desc"], "default": "desc"},
    **pagination_properties,
}
PAGED_RESULT_NOTE = (
    " Results are paginated: the response has items, total, limit, offset, hasMore and nextOffset."
    " If hasMore is true, call again with offset=nextOffset to fetch more."
)


def list_schema(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


def text_content(payload: object) -> list[dict[str, str]]:
    return [{"type": "text", "text": json.dumps(payload, default=str)}]


async def _list_income(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    return await handle_list_transactions(db, auth, "income", arguments)


async def _list_expenses(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    return await handle_list_transactions(db, auth, "expense", arguments)


async def _create_income(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    return await handle_create_transaction(db, auth, "income", arguments)


async def _create_expense(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    return await handle_create_transaction(db, auth, "expense", arguments)


async def _update_income(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    return await handle_update_transaction(db, auth, "income", arguments)


async def _update_expense(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    return await handle_update_transaction(db, auth, "expense", arguments)


async def _delete_income(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    return await handle_delete_transaction(db, auth, "income", arguments)


async def _delete_expense(db: AsyncSession, auth: McpApiKeyAuth, arguments: dict) -> object:
    return await handle_delete_transaction(db, auth, "expense", arguments)


TOOLS = [
    ToolDefinition(
        "list_categories",
        "List income or expense categories in this business, sorted by name, including each category's"
        " custom fields. Use search to filter by name." + PAGED_RESULT_NOTE,
        list_schema(
            {
                "type": category_type_property,
                "search": {
                    "type": "string",
                    "maxLength": MAX_SEARCH_LENGTH,
                    "description": "Case-insensitive match on category name.",
                },
                **pagination_properties,
            },
            ["type"],
        ),
        handle_list_categories,
    ),
    ToolDefinition(
        "create_category",
        "Create an income or expense category in this business.",
        list_schema(
            {
                "name": {"type": "string"},
                "type": category_type_property,
                "customFields": custom_fields_property,
            },
            ["name", "type"],
        ),
        handle_create_category,
        writes=True,
    ),
    ToolDefinition(
        "list_income",
        "List income entries, newest first by default, with optional date range, search and sorting."
        " The summary field has the count, total, average and categories used across ALL matching"
        " entries, so use it for totals instead of paging through everything." + PAGED_RESULT_NOTE,
        list_schema(transaction_list_properties),
        _list_income,
    ),
    ToolDefinition(
        "create_income",
        "Create an income entry.",
        list_schema(transaction_payload_properties, ["date", "categoryId", "amount"]),
        _create_income,
        writes=True,
    ),
    ToolDefinition(
        "update_income",
        "Update an income entry.",
        list_schema({"id": {"type": "string"}, **transaction_payload_properties}, ["id"]),
        _update_income,
        writes=True,
    ),
    ToolDefinition(
        "delete_income",
        "Delete an income entry.",
        list_schema({"id": {"type": "string"}}, ["id"]),
        _delete_income,
        writes=True,
    ),
    ToolDefinition(
        "list_expenses",
        "List expense entries, newest first by default, with optional date range, search and sorting."
        " The summary field has the count, total, average and categories used across ALL matching"
        " entries, so use it for totals instead of paging through everything." + PAGED_RESULT_NOTE,
        list_schema(transaction_list_properties),
        _list_expenses,
    ),
    ToolDefinition(
        "create_expense",
        "Create an expense entry.",
        list_schema(transaction_payload_properties, ["date", "categoryId", "amount"]),
        _create_expense,
        writes=True,
    ),
    ToolDefinition(
        "update_expense",
        "Update an expense entry.",
        list_schema({"id": {"type": "string"}, **transaction_payload_properties}, ["id"]),
        _update_expense,
        writes=True,
    ),
    ToolDefinition(
        "delete_expense",
        "Delete an expense entry.",
        list_schema({"id": {"type": "string"}}, ["id"]),
        _delete_expense,
        writes=True,
    ),
]

TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def can_use(tool: ToolDefinition, auth: McpApiKeyAuth) -> bool:
    return not tool.writes or auth.role in WRITE_FINANCE_ROLES


def tools_for(auth: McpApiKeyAuth) -> list[ToolDefinition]:
    return [tool for tool in TOOLS if can_use(tool, auth)]


async def call_tool(db: AsyncSession, auth: McpApiKeyAuth, name: str, arguments: dict) -> dict:
    tool = TOOLS_BY_NAME.get(name)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")
    if not can_use(tool, auth):
        message = f"Your role ({auth.role}) has read-only access to this business; {name} is not allowed."
        return {"content": text_content({"error": message}), "isError": True}
    payload = await tool.handler(db, auth, arguments)
    return {"content": text_content(payload), "isError": False}
