from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.errors import INTERNAL_ERROR, INVALID_PARAMS, INVALID_REQUEST, METHOD_NOT_FOUND, json_rpc_error
from app.mcp.schemas import JsonRpcRequest
from app.mcp.tool_registry import TOOLS, call_tool

SERVER_INFO = {"name": "farm-accounts-mcp", "version": "0.1.0"}


def json_rpc_result(request_id, result: dict[str, Any]) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": jsonable_encoder(result)}


async def handle_json_rpc_message(
    db: AsyncSession,
    user_id: UUID,
    body: dict,
) -> dict | None:
    try:
        request = JsonRpcRequest(**body)
    except ValidationError:
        return json_rpc_error(INVALID_REQUEST, "Invalid JSON-RPC request", body.get("id"))

    if request.jsonrpc != "2.0":
        return json_rpc_error(INVALID_REQUEST, "jsonrpc must be 2.0", request.id)

    if request.method == "notifications/initialized":
        return None
    if request.method == "initialize":
        return json_rpc_result(
            request.id,
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )
    if request.method == "ping":
        return json_rpc_result(request.id, {})
    if request.method == "tools/list":
        return json_rpc_result(request.id, {"tools": [tool.to_mcp() for tool in TOOLS]})
    if request.method == "tools/call":
        params = request.params or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return json_rpc_error(INVALID_PARAMS, "tools/call requires name and arguments", request.id)
        try:
            result = await call_tool(db, user_id, name, arguments)
        except ValueError as exc:
            return json_rpc_error(INVALID_PARAMS, str(exc), request.id)
        except Exception as exc:
            return json_rpc_error(INTERNAL_ERROR, str(exc), request.id)
        return json_rpc_result(request.id, result)

    return json_rpc_error(METHOD_NOT_FOUND, f"Method not found: {request.method}", request.id)
