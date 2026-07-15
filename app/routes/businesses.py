from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import BusinessAccess, get_business_access, get_current_user_id, require_business_role
from app.schemas.business import BusinessCreate, BusinessDetailResponse, BusinessInvitationCreate, BusinessInvitationResponse, BusinessMemberResponse, BusinessResponse
from app.services import business_service

router = APIRouter()


@router.get("", response_model=list[BusinessResponse])
async def list_accessible_businesses(
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> list[BusinessResponse]:
    return await business_service.list_businesses(db, user_id)


@router.post("", response_model=BusinessResponse, status_code=status.HTTP_201_CREATED)
async def create_business(
    payload: BusinessCreate,
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> BusinessResponse:
    return await business_service.create_business(db, payload, user_id)


@router.get("/{business_id}", response_model=BusinessDetailResponse)
async def get_business(
    business_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> BusinessDetailResponse:
    return await business_service.get_business_detail(db, business_id, user_id)


@router.get("/{business_id}/members", response_model=list[BusinessMemberResponse])
async def list_members(
    business_id: str,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> list[BusinessMemberResponse]:
    if str(access.business.id) != business_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Business header does not match route")
    return await business_service.list_members(db, access.business.id)


@router.get("/{business_id}/invitations", response_model=list[BusinessInvitationResponse])
async def list_invitations(
    business_id: str,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin")),
) -> list[BusinessInvitationResponse]:
    if str(access.business.id) != business_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Business header does not match route")
    return await business_service.list_invitations(db, access.business.id)


@router.post("/{business_id}/invitations", response_model=BusinessInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    business_id: str,
    payload: BusinessInvitationCreate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin")),
) -> BusinessInvitationResponse:
    if str(access.business.id) != business_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Business header does not match route")
    return await business_service.create_invitation(
        db, access.business.id, payload, access.user.id, access.membership.role
    )
