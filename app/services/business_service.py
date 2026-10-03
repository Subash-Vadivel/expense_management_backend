from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import business_delete_attempt_limiter, business_delete_code_limiter
from app.core.security import generate_token, hash_token
from app.models.business import BusinessEntity, BusinessInvitation, BusinessMembership
from app.models.common import parse_uuid
from app.models.user import User
from app.models.user_token import UserToken
from app.repositories import business_repository, user_token_repository
from app.services import email_service
from app.schemas.business import (
    BusinessCreate,
    BusinessDeleteCodeResponse,
    BusinessDetailResponse,
    BusinessInvitationCreate,
    BusinessInvitationResponse,
    BusinessMemberResponse,
    BusinessResponse,
    BusinessUpdate,
    InvitationAcceptResponse,
    InvitationInspectResponse,
)

MANAGE_USERS_ROLES = {"owner", "admin"}
WRITE_FINANCE_ROLES = {"owner", "admin", "manager"}
MANAGE_MCP_ROLES = {"owner", "admin"}
ALL_ROLES = {"owner", "admin", "manager", "viewer"}
DELETE_BUSINESS_PURPOSE = "delete_business"
DELETE_CODE_EXPIRE_MINUTES = 10


def normalize_email(email: str | EmailStr) -> str:
    return str(email).strip().lower()


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
    inviter: User,
    inviter_role: str,
    background_tasks: BackgroundTasks,
) -> BusinessInvitationResponse:
    invited_by = inviter.id
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

    token = generate_token()
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
    invite_url = build_invite_url(token)
    background_tasks.add_task(
        email_service.send_invitation_email, email, business.name, inviter.name, payload.role, invite_url
    )
    return invitation_to_response(created, business, invite_url)


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
    if user.email_verified_at is None:
        # The invite link was delivered to this address, which proves ownership.
        user.email_verified_at = datetime.utcnow()
        db.add(user)
    membership = await business_repository.upsert_membership(db, membership)

    invitation.status = "accepted"
    invitation.accepted_by = user.id
    invitation.accepted_at = datetime.utcnow()
    await business_repository.update_invitation(db, invitation)
    return InvitationAcceptResponse(business=business_to_response(business, membership))


def clean_name(value: str) -> str:
    return " ".join(value.strip().split())


async def update_business(
    db: AsyncSession,
    business: BusinessEntity,
    membership: BusinessMembership,
    payload: BusinessUpdate,
) -> BusinessResponse:
    name = clean_name(payload.name)
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required")
    business.name = name
    business.legal_name = clean_name(payload.legalName) if payload.legalName and payload.legalName.strip() else None
    business.updated_at = datetime.utcnow()
    updated = await business_repository.update_business(db, business)
    return business_to_response(updated, membership)


def delete_code_hash(business_id: UUID, user_id: UUID, code: str) -> str:
    # Bind the code to this business and user so it can't be replayed elsewhere.
    return hash_token(f"{business_id}:{user_id}:{code}")


def rate_limited(message: str, retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"code": "rate_limited", "message": message, "retryAfterSeconds": retry_after},
    )


async def send_delete_code(
    db: AsyncSession,
    business: BusinessEntity,
    user: User,
    background_tasks: BackgroundTasks,
) -> BusinessDeleteCodeResponse:
    limit_key = f"{user.id}:{business.id}"
    if not business_delete_code_limiter.hit(limit_key):
        raise rate_limited(
            "Too many codes requested.", business_delete_code_limiter.retry_after_seconds(limit_key)
        )
    code = f"{secrets.randbelow(1_000_000):06d}"
    await user_token_repository.invalidate_tokens_for_user(db, user.id, DELETE_BUSINESS_PURPOSE)
    await user_token_repository.create_token(
        db,
        UserToken(
            user_id=user.id,
            purpose=DELETE_BUSINESS_PURPOSE,
            token_hash=delete_code_hash(business.id, user.id, code),
            expires_at=datetime.utcnow() + timedelta(minutes=DELETE_CODE_EXPIRE_MINUTES),
        ),
    )
    business_delete_attempt_limiter.reset(limit_key)
    background_tasks.add_task(
        email_service.send_business_delete_code_email,
        user.email,
        user.name,
        business.name,
        code,
        DELETE_CODE_EXPIRE_MINUTES,
    )
    return BusinessDeleteCodeResponse(
        message=f"We sent a 6-digit code to {user.email}.",
        expiresInMinutes=DELETE_CODE_EXPIRE_MINUTES,
    )


async def delete_business(db: AsyncSession, business: BusinessEntity, user: User, code: str) -> None:
    limit_key = f"{user.id}:{business.id}"
    if not business_delete_attempt_limiter.hit(limit_key):
        raise rate_limited(
            "Too many incorrect codes. Request a new code.",
            business_delete_attempt_limiter.retry_after_seconds(limit_key),
        )
    token = await user_token_repository.find_valid_token(
        db, delete_code_hash(business.id, user.id, code), DELETE_BUSINESS_PURPOSE
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_code", "message": "The code is incorrect or has expired"},
        )
    await user_token_repository.invalidate_tokens_for_user(db, user.id, DELETE_BUSINESS_PURPOSE)
    await business_repository.delete_business(db, business.id)
    await db.commit()
    business_delete_attempt_limiter.reset(limit_key)
