from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CategoryType = Literal["income", "expense"]
CustomFieldType = Literal["NUMBER", "STRING", "BOOLEAN"]


class CustomFieldCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: CustomFieldType
    required: bool = False


class CustomFieldResponse(CustomFieldCreate):
    id: str


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: CategoryType
    customFields: list[CustomFieldCreate] = Field(default_factory=list)


class CategoryResponse(BaseModel):
    id: str
    name: str
    type: CategoryType
    customFields: list[CustomFieldResponse] = Field(default_factory=list)
    createdBy: str
    createdAt: datetime
