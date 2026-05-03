from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PyObjectId

TransactionType = Literal["income", "expense"]


class TransactionModel(BaseModel):
    id: PyObjectId | None = Field(default=None, alias="_id")
    date: date
    category_id: PyObjectId = Field(alias="categoryId")
    category_name: str = Field(alias="categoryName")
    description: str | None = None
    amount: float
    type: TransactionType
    created_by: PyObjectId = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    def to_mongo(self) -> dict[str, Any]:
        data = {
            "date": datetime.combine(self.date, time.min, tzinfo=timezone.utc),
            "categoryId": self.category_id,
            "categoryName": self.category_name,
            "description": self.description,
            "amount": self.amount,
            "type": self.type,
            "createdBy": self.created_by,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.id is not None:
            data["_id"] = self.id
        return data
