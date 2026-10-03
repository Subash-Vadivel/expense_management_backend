from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.tools.categories import handle_create_category, handle_delete_category, handle_list_categories
from app.mcp.tools.summary import handle_get_summary
from app.mcp.tools.reports import (
    handle_create_report,
    handle_create_widget,
    handle_delete_report,
    handle_delete_widget,
    handle_get_report,
    handle_get_widget_data,
    handle_list_reports,
    handle_update_report,
    handle_update_widget,
)
from app.mcp.tools.transactions import (
    handle_create_transaction,
    handle_delete_transaction,
    handle_list_transactions,
    handle_update_transaction,
)
from app.mcp.tools.workspaces import handle_create_workspace, handle_list_workspaces
from app.mcp.workspace import ToolAccessError, WorkspaceContext, resolve_workspace
from app.schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, MAX_SEARCH_LENGTH
from app.schemas.report import MAX_SERIES
from app.services.mcp_api_key_service import McpApiKeyAuth

# Workspace tools get a WorkspaceContext; account tools get the key's McpApiKeyAuth.
ToolHandler = Callable[[AsyncSession, Any, dict[str, Any]], Awaitable[object]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler
    # Write tools need a role in WRITE_FINANCE_ROLES in the target workspace, matching the REST routes.
    writes: bool = False
    # "workspace": requires workspaceId (added to the schema here); "account": acts on the key's user.
    scope: Literal["workspace", "account"] = "workspace"

    def to_mcp(self) -> dict[str, Any]:
        schema = self.input_schema
        if self.scope == "workspace":
            schema = {
                **schema,
                "properties": {"workspaceId": workspace_id_property, **schema["properties"]},
                "required": ["workspaceId", *schema["required"]],
            }
        return {"name": self.name, "description": self.description, "inputSchema": schema}


workspace_id_property = {
    "type": "string",
    "description": "Id of the workspace to act on. Get it from list_workspaces.",
}
category_type_property = {"type": "string", "enum": ["income", "expense"]}
custom_fields_property = {
    "type": "array",
    "description": "Structured fields recorded on each entry of this category. Use NUMBER for quantities and"
    " prices you will want to chart (sum/average), STRING for text, BOOLEAN for yes/no.",
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

# --- report widget schema ----------------------------------------------------------------------

series_property = {
    "type": "object",
    "description": "One line/bar/area, pie slice, or the KPI value: an aggregate of one category's entries.",
    "properties": {
        "id": {"type": "string", "description": "Any id unique within this widget, e.g. \"s1\"."},
        "categoryId": {"type": "string", "description": "Category id from list_categories (income or expense)."},
        "label": {
            "type": ["string", "null"],
            "maxLength": 80,
            "description": "Legend label. Omit to use \"<category> · <metric>\".",
        },
        "metric": {
            "type": "object",
            "description": "What to aggregate: the entry amount, or one of the category's custom fields.",
            "oneOf": [
                {
                    "type": "object",
                    "properties": {"kind": {"const": "amount"}},
                    "required": ["kind"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "kind": {"const": "field"},
                        "fieldId": {
                            "type": "string",
                            "description": "A custom field id from the category's customFields (list_categories).",
                        },
                    },
                    "required": ["kind", "fieldId"],
                    "additionalProperties": False,
                },
            ],
        },
        "aggregation": {
            "type": "string",
            "enum": ["sum", "avg", "min", "max", "count", "percent"],
            "description": "How entries combine per day/week/month (or over the range for pie/donut/kpi)."
            " Allowed by metric: amount -> sum|avg|min|max|count (count = number of entries);"
            " NUMBER field -> sum|avg|min|max (use avg for rates like price/kg, sum for quantities);"
            " STRING/BOOLEAN field -> count|percent (entries where the field is filled, or true for BOOLEAN;"
            " percent = that share of the category's entries).",
        },
    },
    "required": ["id", "categoryId", "metric", "aggregation"],
    "additionalProperties": False,
}
widget_config_property = {
    "type": "object",
    "properties": {
        "interval": {
            "type": "string",
            "enum": ["day", "week", "month"],
            "default": "month",
            "description": "Date bucket for line/area/bar (weeks start Monday; daily is capped at 366 days)."
            " Ignored for pie, donut and kpi.",
        },
        "dateRange": {
            "type": "object",
            "description": "{\"mode\": \"report\"} follows the report's date filter chosen by the viewer (default,"
            " recommended). {\"mode\": \"custom\", \"startDate\": \"YYYY-MM-DD\", \"endDate\": \"YYYY-MM-DD\"} pins"
            " this widget to a fixed range.",
            "oneOf": [
                {
                    "type": "object",
                    "properties": {"mode": {"const": "report"}},
                    "required": ["mode"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "mode": {"const": "custom"},
                        "startDate": {"type": "string", "format": "date"},
                        "endDate": {"type": "string", "format": "date"},
                    },
                    "required": ["mode", "startDate", "endDate"],
                    "additionalProperties": False,
                },
            ],
        },
        "series": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_SERIES,
            "description": f"1-{MAX_SERIES} series. A kpi takes exactly 1.",
            "items": series_property,
        },
    },
    "required": ["series"],
    "additionalProperties": False,
}
WIDGET_EXAMPLE = json.dumps(
    {
        "reportId": "<report id>",
        "title": "Drumstick price per kg",
        "chartType": "line",
        "config": {
            "interval": "week",
            "dateRange": {"mode": "report"},
            "series": [
                {
                    "id": "s1",
                    "categoryId": "<category id>",
                    "metric": {"kind": "field", "fieldId": "<NUMBER field id>"},
                    "aggregation": "avg",
                }
            ],
        },
    }
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


async def _list_income(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    return await handle_list_transactions(db, ctx, "income", arguments)


async def _list_expenses(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    return await handle_list_transactions(db, ctx, "expense", arguments)


async def _create_income(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    return await handle_create_transaction(db, ctx, "income", arguments)


async def _create_expense(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    return await handle_create_transaction(db, ctx, "expense", arguments)


async def _update_income(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    return await handle_update_transaction(db, ctx, "income", arguments)


async def _update_expense(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    return await handle_update_transaction(db, ctx, "expense", arguments)


async def _delete_income(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    return await handle_delete_transaction(db, ctx, "income", arguments)


async def _delete_expense(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    return await handle_delete_transaction(db, ctx, "expense", arguments)


TOOLS = [
    # --- account ---------------------------------------------------------------------------------
    ToolDefinition(
        "list_workspaces",
        "List the workspaces (businesses) you can access, with your role in each: owner, admin, manager"
        " (can change data) or viewer (read-only). Call this first: every other tool except"
        " create_workspace needs a workspaceId from here.",
        list_schema(),
        handle_list_workspaces,
        scope="account",
    ),
    ToolDefinition(
        "create_workspace",
        "Create a new workspace (a separate set of books for a business, shop, farm or household)."
        " You become its owner. Returns its id for use as workspaceId.",
        list_schema(
            {
                "name": {"type": "string", "minLength": 1, "maxLength": 120, "description": "Display name."},
                "legalName": {
                    "type": ["string", "null"],
                    "maxLength": 180,
                    "description": "Optional registered business name.",
                },
            },
            ["name"],
        ),
        handle_create_workspace,
        writes=True,
        scope="account",
    ),
    # --- categories & ledgers --------------------------------------------------------------------
    ToolDefinition(
        "list_categories",
        "List income or expense categories in the workspace, sorted by name, including each category's"
        " custom fields (id, name, type). Category ids and custom field ids are what report widgets"
        " chart. Use search to filter by name." + PAGED_RESULT_NOTE,
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
        "Create an income or expense category in the workspace, optionally with custom fields.",
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
        "delete_category",
        "Delete a category from the workspace. Refused if any income or expense entries use it (delete or"
        " move those entries first). Report widgets charting it will show an error until edited.",
        list_schema({"categoryId": {"type": "string", "description": "Category id from list_categories."}}, ["categoryId"]),
        handle_delete_category,
        writes=True,
    ),
    ToolDefinition(
        "get_summary",
        "Workspace totals for a date range in one call: totalIncome, totalExpense, netBalance, and the top 5"
        " income and expense categories by amount. Use this for \"how are we doing\" questions instead of"
        " paging through list_income/list_expenses. Omit both dates for all time.",
        list_schema(
            {
                "startDate": {"type": "string", "format": "date", "description": "Range start (YYYY-MM-DD), inclusive."},
                "endDate": {"type": "string", "format": "date", "description": "Range end (YYYY-MM-DD), inclusive."},
            }
        ),
        handle_get_summary,
    ),
    ToolDefinition(
        "list_income",
        "List income entries in the workspace, newest first by default, with optional date range, search and"
        " sorting. The summary field has the count, total, average and categories used across ALL matching"
        " entries, so use it for totals instead of paging through everything." + PAGED_RESULT_NOTE,
        list_schema(transaction_list_properties),
        _list_income,
    ),
    ToolDefinition(
        "create_income",
        "Create an income entry in the workspace.",
        list_schema(transaction_payload_properties, ["date", "categoryId", "amount"]),
        _create_income,
        writes=True,
    ),
    ToolDefinition(
        "update_income",
        "Update an income entry in the workspace. Only the fields you pass are changed.",
        list_schema({"id": {"type": "string"}, **transaction_payload_properties}, ["id"]),
        _update_income,
        writes=True,
    ),
    ToolDefinition(
        "delete_income",
        "Delete an income entry from the workspace.",
        list_schema({"id": {"type": "string"}}, ["id"]),
        _delete_income,
        writes=True,
    ),
    ToolDefinition(
        "list_expenses",
        "List expense entries in the workspace, newest first by default, with optional date range, search and"
        " sorting. The summary field has the count, total, average and categories used across ALL matching"
        " entries, so use it for totals instead of paging through everything." + PAGED_RESULT_NOTE,
        list_schema(transaction_list_properties),
        _list_expenses,
    ),
    ToolDefinition(
        "create_expense",
        "Create an expense entry in the workspace.",
        list_schema(transaction_payload_properties, ["date", "categoryId", "amount"]),
        _create_expense,
        writes=True,
    ),
    ToolDefinition(
        "update_expense",
        "Update an expense entry in the workspace. Only the fields you pass are changed.",
        list_schema({"id": {"type": "string"}, **transaction_payload_properties}, ["id"]),
        _update_expense,
        writes=True,
    ),
    ToolDefinition(
        "delete_expense",
        "Delete an expense entry from the workspace.",
        list_schema({"id": {"type": "string"}}, ["id"]),
        _delete_expense,
        writes=True,
    ),
    # --- reports ---------------------------------------------------------------------------------
    ToolDefinition(
        "list_reports",
        "List the workspace's reports: dashboards of chart widgets that everyone in the workspace sees."
        " Returns id, name, description and widgetCount.",
        list_schema(),
        handle_list_reports,
    ),
    ToolDefinition(
        "get_report",
        "Get one report with its widgets (id, title, chartType, config, layout). Use it to see what a report"
        " already shows before adding or removing widgets.",
        list_schema({"reportId": {"type": "string", "description": "Report id from list_reports."}}, ["reportId"]),
        handle_get_report,
    ),
    ToolDefinition(
        "get_widget_data",
        "Compute a widget's numbers: for line/area/bar the buckets (day/week/month) with each series' values"
        " (null = no entries that period) and total; for pie/donut each series' total; for kpi the total and"
        " previousTotal (same aggregate over the equally long period just before the range). Use it to answer"
        " questions from a report or to check a widget you built shows data. Reports have no saved date range"
        " (each viewer picks one), so pass startDate/endDate, or omit both for all time; widgets pinned to"
        " their own range ignore them.",
        list_schema(
            {
                "reportId": {"type": "string", "description": "Report id."},
                "widgetId": {"type": "string", "description": "Widget id from get_report."},
                "startDate": {"type": "string", "format": "date", "description": "Range start (YYYY-MM-DD), inclusive."},
                "endDate": {"type": "string", "format": "date", "description": "Range end (YYYY-MM-DD), inclusive."},
            },
            ["reportId", "widgetId"],
        ),
        handle_get_widget_data,
    ),
    ToolDefinition(
        "create_report",
        "Create an empty report (a dashboard) in the workspace, then add charts with create_widget."
        " Group related charts in one report, e.g. \"Vegetable prices\" or \"Monthly expenses\"."
        " Viewers pick the date range on the report; widgets follow it unless pinned to their own range.",
        list_schema(
            {
                "name": {"type": "string", "minLength": 1, "maxLength": 120, "description": "Report title."},
                "description": {
                    "type": ["string", "null"],
                    "maxLength": 500,
                    "description": "Optional one-line summary of what the report tracks.",
                },
            },
            ["name"],
        ),
        handle_create_report,
        writes=True,
    ),
    ToolDefinition(
        "update_report",
        "Rename a report or change its description. Only the fields you pass change; description null clears it.",
        list_schema(
            {
                "reportId": {"type": "string", "description": "Report id from list_reports."},
                "name": {"type": "string", "minLength": 1, "maxLength": 120},
                "description": {"type": ["string", "null"], "maxLength": 500},
            },
            ["reportId"],
        ),
        handle_update_report,
        writes=True,
    ),
    ToolDefinition(
        "delete_report",
        "Delete a report and all of its widgets. Ledger data (entries, categories) is not affected.",
        list_schema({"reportId": {"type": "string", "description": "Report id from list_reports."}}, ["reportId"]),
        handle_delete_report,
        writes=True,
    ),
    ToolDefinition(
        "create_widget",
        "Add a chart widget to a report. First call list_categories (income and expense) to get category ids"
        " and their custom field ids/types. Chart types: line/area/bar show trends over time on a date axis"
        " (use for prices, quantities or spending over weeks/months); pie/donut compare series totals over the"
        " date range (use for shares, e.g. spend by category); kpi shows one headline number with % change vs"
        " the previous period of the same length (exactly 1 series). Series in one widget may mix amounts and"
        " numbers; they get separate axes. The widget is placed at the bottom of the report at its default"
        f" size. Example arguments: {WIDGET_EXAMPLE}",
        list_schema(
            {
                "reportId": {"type": "string", "description": "Report id from create_report or list_reports."},
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 120,
                    "description": "Short chart title shown on the widget, e.g. \"Monthly feed cost\".",
                },
                "chartType": {"type": "string", "enum": ["line", "area", "bar", "pie", "donut", "kpi"]},
                "config": widget_config_property,
            },
            ["reportId", "title", "chartType", "config"],
        ),
        handle_create_widget,
        writes=True,
    ),
    ToolDefinition(
        "update_widget",
        "Change an existing widget in place; it keeps its id, position and size on the report. Only the"
        " fields you pass change. config replaces the whole config, so call get_report first and send the"
        " full config with your edits (e.g. a different interval, aggregation or extra series). Switching"
        " chartType resizes the widget to fit the new type if needed; switching to kpi requires exactly 1"
        " series. The same config rules as create_widget apply.",
        list_schema(
            {
                "reportId": {"type": "string", "description": "Report id."},
                "widgetId": {"type": "string", "description": "Widget id from get_report."},
                "title": {"type": "string", "minLength": 1, "maxLength": 120, "description": "New title."},
                "chartType": {"type": "string", "enum": ["line", "area", "bar", "pie", "donut", "kpi"]},
                "config": {**widget_config_property, "description": "Full replacement config (see create_widget)."},
            },
            ["reportId", "widgetId"],
        ),
        handle_update_widget,
        writes=True,
    ),
    ToolDefinition(
        "delete_widget",
        "Remove one widget from a report.",
        list_schema(
            {
                "reportId": {"type": "string", "description": "Report id."},
                "widgetId": {"type": "string", "description": "Widget id from get_report."},
            },
            ["reportId", "widgetId"],
        ),
        handle_delete_widget,
        writes=True,
    ),
]

TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def tool_error(message: str) -> dict:
    return {"content": text_content({"error": message}), "isError": True}


def http_error_message(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        return str(detail.get("message") or detail)
    return str(detail)


async def call_tool(db: AsyncSession, auth: McpApiKeyAuth, name: str, arguments: dict) -> dict:
    tool = TOOLS_BY_NAME.get(name)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")
    try:
        if tool.scope == "workspace":
            arguments = dict(arguments)
            ctx = await resolve_workspace(db, auth, arguments.pop("workspaceId", None), tool.writes)
            payload = await tool.handler(db, ctx, arguments)
        else:
            payload = await tool.handler(db, auth, arguments)
    except ToolAccessError as exc:
        return tool_error(str(exc))
    # Service errors (not found, invalid category/field/aggregation...) go back as tool errors the agent can fix.
    except HTTPException as exc:
        return tool_error(http_error_message(exc))
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(str(p) for p in e['loc']) or 'arguments'}: {e['msg']}" for e in exc.errors())
        return tool_error(f"Invalid arguments: {problems}")
    return {"content": text_content(payload), "isError": False}
