from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel

CategoryType = Literal["income", "expense"]
CustomFieldType = Literal["NUMBER", "STRING", "BOOLEAN"]


def utc_now() -> datetime:
    return datetime.utcnow()


class CustomFieldDefinition(SQLModel):
    id: str
    name: str
    type: CustomFieldType
    required: bool = False


class Category(SQLModel, table=True):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("created_by", "type", "normalized_name", name="uq_categories_owner_type_name"),
        Index("ix_categories_owner_type_name", "created_by", "type", "name"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    normalized_name: str = Field(index=True)
    type: str = Field(index=True)
    custom_fields: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_by: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(default_factory=utc_now)
