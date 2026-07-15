from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

BusinessRole = Literal["owner", "admin", "manager", "viewer"]


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    legalName: str | None = Field(default=None, max_length=180)


class BusinessResponse(BaseModel):
    id: str
    name: str
    legalName: str | None = None
    role: BusinessRole
    createdBy: str
    createdAt: datetime


class BusinessDetailResponse(BusinessResponse):
    memberCount: int = 0


class BusinessMemberResponse(BaseModel):
    id: str
    userId: str
    name: str
    email: EmailStr
    role: BusinessRole
    status: str
    createdAt: datetime


class BusinessInvitationCreate(BaseModel):
    email: EmailStr
    role: BusinessRole


class BusinessInvitationResponse(BaseModel):
    id: str
    businessId: str
    businessName: str
    email: EmailStr
    role: BusinessRole
    status: str
    invitedBy: str
    acceptedBy: str | None = None
    expiresAt: datetime
    createdAt: datetime
    inviteUrl: str | None = None


class InvitationInspectResponse(BaseModel):
    businessId: str
    businessName: str
    email: EmailStr
    role: BusinessRole
    status: str
    expiresAt: datetime


class InvitationAcceptResponse(BaseModel):
    business: BusinessResponse
