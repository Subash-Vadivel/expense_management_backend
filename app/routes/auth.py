from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import get_current_user
from app.schemas.auth import (
    EmailRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    TokenRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter()


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(
    payload: SignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
) -> SignupResponse:
    return await auth_service.signup(db, payload, background_tasks)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_session)) -> TokenResponse:
    return await auth_service.login(db, payload)


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(payload: TokenRequest, db: AsyncSession = Depends(get_session)) -> TokenResponse:
    return await auth_service.verify_email(db, payload.token)


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    payload: EmailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    return await auth_service.resend_verification(db, payload.email, background_tasks)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: EmailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    return await auth_service.forgot_password(db, payload.email, background_tasks)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_session)) -> MessageResponse:
    return await auth_service.reset_password(db, payload)


@router.get("/me", response_model=UserResponse)
async def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
