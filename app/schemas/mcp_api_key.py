from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class McpApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class McpApiKeyUpdate(BaseModel):
    enabled: bool


class McpApiKeyResponse(BaseModel):
    id: str
    name: str
    keyPrefix: str
    enabled: bool
    createdAt: datetime
    lastUsedAt: datetime | None = None
    disabledAt: datetime | None = None


class McpApiKeyCreateResponse(McpApiKeyResponse):
    apiKey: str
