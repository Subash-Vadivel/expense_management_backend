from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PyObjectId

CategoryType = Literal["income", "expense"]


class CategoryModel(BaseModel):
    id: PyObjectId | None = Field(default=None, alias="_id")
    name: str
    normalized_name: str = Field(alias="normalizedName")
    type: CategoryType
    created_by: PyObjectId = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    def to_mongo(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "normalizedName": self.normalized_name,
            "type": self.type,
            "createdBy": self.created_by,
            "createdAt": self.created_at,
        }
        if self.id is not None:
            data["_id"] = self.id
        return data
