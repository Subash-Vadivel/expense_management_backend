from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import get_current_user_document
from app.models.user import User
from app.schemas.business import InvitationAcceptResponse, InvitationInspectResponse
from app.services import business_service

router = APIRouter()


@router.get("/{token}", response_model=InvitationInspectResponse)
async def inspect_invitation(token: str, db: AsyncSession = Depends(get_session)) -> InvitationInspectResponse:
    return await business_service.inspect_invitation(db, token)


@router.post("/{token}/accept", response_model=InvitationAcceptResponse)
async def accept_invitation(
    token: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_document),
) -> InvitationAcceptResponse:
    return await business_service.accept_invitation(db, token, user)
