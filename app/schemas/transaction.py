from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

TransactionType = Literal["income", "expense"]


class TransactionCreate(BaseModel):
    date: date
    categoryId: str
    description: str | None = Field(default=None, max_length=500)
    amount: float = Field(gt=0)


class TransactionUpdate(BaseModel):
    date: date | None = None
    categoryId: str | None = None
    description: str | None = Field(default=None, max_length=500)
    amount: float | None = Field(default=None, gt=0)


class TransactionResponse(BaseModel):
    id: str
    date: date
    categoryId: str
    categoryName: str
    description: str | None
    amount: float
    type: TransactionType
    createdAt: datetime
    updatedAt: datetime
