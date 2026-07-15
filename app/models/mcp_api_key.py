from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.utcnow()


class McpApiKey(SQLModel, table=True):
    __tablename__ = "mcp_api_keys"
    __table_args__ = (Index("ix_mcp_api_keys_business_created", "business_id", "created_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    key_hash: str = Field(index=True, unique=True)
    key_prefix: str
    enabled: bool = Field(default=True, index=True)
    business_id: UUID = Field(sa_column=Column(ForeignKey("business_entities.id", ondelete="CASCADE"), nullable=False, index=True))
    created_by: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(default_factory=utc_now)
    last_used_at: datetime | None = None
    disabled_at: datetime | None = None
