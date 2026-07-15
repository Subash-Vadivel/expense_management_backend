from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.tools.categories import handle_create_category, handle_list_categories
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
        "List income or expense categories for the authenticated user.",
        list_schema({"type": category_type_property}, ["type"]),
        handle_list_categories,
    ),
    ToolDefinition(
        "create_category",
        "Create an income or expense category for the authenticated user.",
        list_schema(
            {
                "name": {"type": "string"},
                "type": category_type_property,
                "customFields": custom_fields_property,
            },
            ["name", "type"],
        ),
        handle_create_category,
    ),
    ToolDefinition(
        "list_income",
        "List income entries with optional startDate and endDate filters.",
        list_schema({"startDate": {"type": "string", "format": "date"}, "endDate": {"type": "string", "format": "date"}}),
        _list_income,
    ),
    ToolDefinition(
        "create_income",
        "Create an income entry.",
        list_schema(transaction_payload_properties, ["date", "categoryId", "amount"]),
        _create_income,
    ),
    ToolDefinition(
        "update_income",
        "Update an income entry.",
        list_schema({"id": {"type": "string"}, **transaction_payload_properties}, ["id"]),
        _update_income,
    ),
    ToolDefinition(
        "delete_income",
        "Delete an income entry.",
        list_schema({"id": {"type": "string"}}, ["id"]),
        _delete_income,
    ),
    ToolDefinition(
        "list_expenses",
        "List expense entries with optional startDate and endDate filters.",
        list_schema({"startDate": {"type": "string", "format": "date"}, "endDate": {"type": "string", "format": "date"}}),
        _list_expenses,
    ),
    ToolDefinition(
        "create_expense",
        "Create an expense entry.",
        list_schema(transaction_payload_properties, ["date", "categoryId", "amount"]),
        _create_expense,
    ),
    ToolDefinition(
        "update_expense",
        "Update an expense entry.",
        list_schema({"id": {"type": "string"}, **transaction_payload_properties}, ["id"]),
        _update_expense,
    ),
    ToolDefinition(
        "delete_expense",
        "Delete an expense entry.",
        list_schema({"id": {"type": "string"}}, ["id"]),
        _delete_expense,
    ),
]

TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


async def call_tool(db: AsyncSession, auth: McpApiKeyAuth, name: str, arguments: dict) -> dict:
    tool = TOOLS_BY_NAME.get(name)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")
    payload = await tool.handler(db, auth, arguments)
    return {"content": text_content(payload), "isError": False}
