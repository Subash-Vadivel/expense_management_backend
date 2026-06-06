from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PyObjectId


class McpApiKeyModel(BaseModel):
    id: PyObjectId | None = Field(default=None, alias="_id")
    name: str
    key_hash: str = Field(alias="keyHash")
    key_prefix: str = Field(alias="keyPrefix")
    enabled: bool = True
    created_by: PyObjectId = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")
    last_used_at: datetime | None = Field(default=None, alias="lastUsedAt")
    disabled_at: datetime | None = Field(default=None, alias="disabledAt")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    def to_mongo(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "keyHash": self.key_hash,
            "keyPrefix": self.key_prefix,
            "enabled": self.enabled,
            "createdBy": self.created_by,
            "createdAt": self.created_at,
        }
        if self.last_used_at is not None:
            data["lastUsedAt"] = self.last_used_at
        if self.disabled_at is not None:
            data["disabledAt"] = self.disabled_at
        if self.id is not None:
            data["_id"] = self.id
        return data
