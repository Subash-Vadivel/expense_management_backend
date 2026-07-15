from __future__ import annotations

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mcp_api_key_service import McpApiKeyAuth, authenticate_api_key


def extract_api_key(authorization: str | None, x_api_key: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return x_api_key


async def authenticate_mcp_user(
    db: AsyncSession,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> McpApiKeyAuth:
    raw_key = extract_api_key(authorization, x_api_key)
    if not raw_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MCP API key is required")
    auth = await authenticate_api_key(db, raw_key)
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MCP API key")
    return auth
