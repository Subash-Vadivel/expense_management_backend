from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.mcp.errors import PARSE_ERROR, json_rpc_error
from app.mcp.protocol import handle_json_rpc_message
from app.mcp.security import authenticate_mcp_user

router = APIRouter()


@router.post("/mcp")
async def mcp_endpoint(
    body=Body(...),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_session),
):
    user_id: UUID = await authenticate_mcp_user(db, authorization, x_api_key)
    if not isinstance(body, dict):
        return json_rpc_error(PARSE_ERROR, "Request body must be a JSON object")
    result = await handle_json_rpc_message(db, user_id, body)
    if result is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return result
