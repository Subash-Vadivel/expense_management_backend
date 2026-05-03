from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CategoryType = Literal["income", "expense"]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: CategoryType


class CategoryResponse(BaseModel):
    id: str
    name: str
    type: CategoryType
    createdBy: str
    createdAt: datetime
