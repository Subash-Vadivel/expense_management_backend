from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.utcnow()


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    email: EmailStr = Field(index=True, unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=utc_now)
