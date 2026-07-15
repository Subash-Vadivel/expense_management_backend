from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.business import BusinessEntity, BusinessInvitation, BusinessMembership
from app.models.common import parse_uuid
from app.models.user import User
from app.repositories import business_repository
from app.schemas.business import (
    BusinessCreate,
    BusinessDetailResponse,
    BusinessInvitationCreate,
    BusinessInvitationResponse,
    BusinessMemberResponse,
    BusinessResponse,
    InvitationAcceptResponse,
    InvitationInspectResponse,
)

MANAGE_USERS_ROLES = {"owner", "admin"}
WRITE_FINANCE_ROLES = {"owner", "admin", "manager"}
MANAGE_MCP_ROLES = {"owner", "admin"}
ALL_ROLES = {"owner", "admin", "manager", "viewer"}


def normalize_email(email: str | EmailStr) -> str:
    return str(email).strip().lower()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def build_invite_url(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/invitations/{token}"


def business_to_response(business: BusinessEntity, membership: BusinessMembership) -> BusinessResponse:
    return BusinessResponse(
        id=str(business.id),
        name=business.name,
        legalName=business.legal_name,
        role=membership.role,
        createdBy=str(business.created_by),
        createdAt=business.created_at,
    )


def business_detail_to_response(
    business: BusinessEntity,
    membership: BusinessMembership,
    member_count: int,
) -> BusinessDetailResponse:
    return BusinessDetailResponse(
        **business_to_response(business, membership).model_dump(),
        memberCount=member_count,
    )


def member_to_response(membership: BusinessMembership, user: User) -> BusinessMemberResponse:
    return BusinessMemberResponse(
        id=str(membership.id),
        userId=str(user.id),
        name=user.name,
        email=user.email,
        role=membership.role,
        status=membership.status,
        createdAt=membership.created_at,
    )


def invitation_to_response(
    invitation: BusinessInvitation,
    business: BusinessEntity,
    invite_url: str | None = None,
) -> BusinessInvitationResponse:
    return BusinessInvitationResponse(
        id=str(invitation.id),
        businessId=str(invitation.business_id),
        businessName=business.name,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        invitedBy=str(invitation.invited_by),
        acceptedBy=str(invitation.accepted_by) if invitation.accepted_by else None,
        expiresAt=invitation.expires_at,
        createdAt=invitation.created_at,
        inviteUrl=invite_url,
    )


async def list_businesses(db: AsyncSession, user_id: UUID) -> list[BusinessResponse]:
    rows = await business_repository.list_active_businesses_for_user(db, user_id)
    return [business_to_response(business, membership) for business, membership in rows]


async def create_business(db: AsyncSession, payload: BusinessCreate, user_id: UUID) -> BusinessResponse:
    business = BusinessEntity(
        name=" ".join(payload.name.strip().split()),
        legal_name=" ".join(payload.legalName.strip().split()) if payload.legalName else None,
        created_by=user_id,
    )
    membership = BusinessMembership(
        business_id=business.id,
        user_id=user_id,
        role="owner",
        status="active",
        invited_by=user_id,
    )
    try:
        created = await business_repository.create_business(db, business, membership)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Business could not be created") from exc
    return business_to_response(created, membership)


async def get_business_detail(db: AsyncSession, business_id: str, user_id: UUID) -> BusinessDetailResponse:
    business_uuid = parse_uuid(business_id, "business id")
    business = await business_repository.get_business(db, business_uuid)
    membership = await business_repository.get_membership(db, business_uuid, user_id)
    if not business or not membership or membership.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    count = await business_repository.count_active_members(db, business_uuid)
    return business_detail_to_response(business, membership, count)


async def get_active_membership(db: AsyncSession, business_id: UUID, user_id: UUID) -> BusinessMembership | None:
    membership = await business_repository.get_membership(db, business_id, user_id)
    if membership and membership.status == "active":
        return membership
    return None


async def list_members(db: AsyncSession, business_id: UUID) -> list[BusinessMemberResponse]:
    rows = await business_repository.list_members(db, business_id)
    return [member_to_response(membership, user) for membership, user in rows]


async def list_invitations(db: AsyncSession, business_id: UUID) -> list[BusinessInvitationResponse]:
    business = await business_repository.get_business(db, business_id)
    invitations = await business_repository.list_invitations(db, business_id)
    return [invitation_to_response(invitation, business) for invitation in invitations]


async def create_invitation(
    db: AsyncSession,
    business_id: UUID,
    payload: BusinessInvitationCreate,
    invited_by: UUID,
    inviter_role: str,
) -> BusinessInvitationResponse:
    email = normalize_email(payload.email)
    if payload.role not in ALL_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    if inviter_role == "admin" and payload.role == "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins cannot invite owners")
    existing_membership = await business_repository.get_membership(db, business_id, invited_by)
    if not existing_membership or existing_membership.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business access required")

    business = await business_repository.get_business(db, business_id)
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    existing_invite = await business_repository.find_pending_invitation_for_email(db, business_id, email)
    if existing_invite:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A pending invitation already exists for this email")

    token = generate_invitation_token()
    invitation = BusinessInvitation(
        business_id=business_id,
        email=email,
        role=payload.role,
        token_hash=hash_token(token),
        status="pending",
        invited_by=invited_by,
        expires_at=datetime.utcnow() + timedelta(days=14),
    )
    created = await business_repository.create_invitation(db, invitation)
    return invitation_to_response(created, business, build_invite_url(token))


async def inspect_invitation(db: AsyncSession, token: str) -> InvitationInspectResponse:
    invitation = await business_repository.find_invitation_by_token_hash(db, hash_token(token))
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if invitation.status == "pending" and invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        await business_repository.update_invitation(db, invitation)
    business = await business_repository.get_business(db, invitation.business_id)
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return InvitationInspectResponse(
        businessId=str(business.id),
        businessName=business.name,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        expiresAt=invitation.expires_at,
    )


async def accept_invitation(db: AsyncSession, token: str, user: User) -> InvitationAcceptResponse:
    invitation = await business_repository.find_invitation_by_token_hash(db, hash_token(token))
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if invitation.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation is not pending")
    if invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        await business_repository.update_invitation(db, invitation)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired")
    if normalize_email(user.email) != invitation.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invitation is for a different email")

    business = await business_repository.get_business(db, invitation.business_id)
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    membership = await business_repository.get_membership(db, invitation.business_id, user.id)
    if membership:
        membership.role = invitation.role
        membership.status = "active"
        membership.invited_by = invitation.invited_by
        membership.updated_at = datetime.utcnow()
    else:
        membership = BusinessMembership(
            business_id=invitation.business_id,
            user_id=user.id,
            role=invitation.role,
            status="active",
            invited_by=invitation.invited_by,
        )
    membership = await business_repository.upsert_membership(db, membership)

    invitation.status = "accepted"
    invitation.accepted_by = user.id
    invitation.accepted_at = datetime.utcnow()
    await business_repository.update_invitation(db, invitation)
    return InvitationAcceptResponse(business=business_to_response(business, membership))
