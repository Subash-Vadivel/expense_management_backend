from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

BusinessRole = Literal["owner", "admin", "manager", "viewer"]
MembershipStatus = Literal["active", "removed"]
InvitationStatus = Literal["pending", "accepted", "revoked", "expired"]


def utc_now() -> datetime:
    return datetime.utcnow()


class BusinessEntity(SQLModel, table=True):
    __tablename__ = "business_entities"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    legal_name: str | None = None
    created_by: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BusinessMembership(SQLModel, table=True):
    __tablename__ = "business_memberships"
    __table_args__ = (
        UniqueConstraint("business_id", "user_id", name="uq_business_membership_business_user"),
        Index("ix_business_memberships_user_status", "user_id", "status"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    business_id: UUID = Field(sa_column=Column(ForeignKey("business_entities.id", ondelete="CASCADE"), nullable=False, index=True))
    user_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    role: str = Field(index=True)
    status: str = Field(default="active", index=True)
    invited_by: UUID | None = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BusinessInvitation(SQLModel, table=True):
    __tablename__ = "business_invitations"
    __table_args__ = (
        Index("ix_business_invitations_business_status", "business_id", "status"),
        Index("ix_business_invitations_email_status", "email", "status"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    business_id: UUID = Field(sa_column=Column(ForeignKey("business_entities.id", ondelete="CASCADE"), nullable=False, index=True))
    email: str = Field(index=True)
    role: str = Field(index=True)
    token_hash: str = Field(index=True, unique=True)
    status: str = Field(default="pending", index=True)
    invited_by: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    accepted_by: UUID | None = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    expires_at: datetime
    created_at: datetime = Field(default_factory=utc_now)
    accepted_at: datetime | None = None
