from __future__ import annotations

from datetime import date as Date, datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, JSON
from sqlmodel import Field, SQLModel

TransactionType = Literal["income", "expense"]
CustomFieldType = Literal["NUMBER", "STRING", "BOOLEAN"]


def utc_now() -> datetime:
    return datetime.utcnow()


class CustomFieldValue(SQLModel):
    field_id: str
    field_name: str
    field_type: CustomFieldType
    value_number: float | None = None
    value_string: str | None = None
    value_boolean: bool | None = None

    def to_payload(self) -> dict:
        data = {
            "fieldId": self.field_id,
            "fieldName": self.field_name,
            "fieldType": self.field_type,
        }
        if self.value_number is not None:
            data["valueNumber"] = self.value_number
        if self.value_string is not None:
            data["valueString"] = self.value_string
        if self.value_boolean is not None:
            data["valueBoolean"] = self.value_boolean
        return data


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_owner_type_date", "created_by", "type", "date"),
        Index("ix_transactions_owner_category", "created_by", "category_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: Date = Field(index=True)
    category_id: UUID = Field(sa_column=Column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True))
    category_name: str
    description: str | None = None
    amount: float
    type: str = Field(index=True)
    custom_field_values: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_by: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
