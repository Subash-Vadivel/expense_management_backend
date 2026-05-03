from __future__ import annotations

from datetime import date as Date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TransactionType = Literal["income", "expense"]
CustomFieldType = Literal["NUMBER", "STRING", "BOOLEAN"]


class CustomFieldValueInput(BaseModel):
    fieldId: str
    value: Any = None


class CustomFieldValueResponse(BaseModel):
    fieldId: str
    fieldName: str
    fieldType: CustomFieldType
    valueNumber: float | None = None
    valueString: str | None = None
    valueBoolean: bool | None = None


class TransactionCreate(BaseModel):
    date: Date
    categoryId: str
    description: str | None = Field(default=None, max_length=500)
    amount: float = Field(gt=0)
    customFieldValues: list[CustomFieldValueInput] = Field(default_factory=list)


class TransactionUpdate(BaseModel):
    date: Date | None = None
    categoryId: str | None = None
    description: str | None = Field(default=None, max_length=500)
    amount: float | None = Field(default=None, gt=0)
    customFieldValues: list[CustomFieldValueInput] | None = None


class TransactionResponse(BaseModel):
    id: str
    date: Date
    categoryId: str
    categoryName: str
    description: str | None
    amount: float
    type: TransactionType
    customFieldValues: list[CustomFieldValueResponse] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime
