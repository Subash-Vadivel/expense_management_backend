from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import SlidingWindowLimiter, password_reset_limiter, verification_resend_limiter
from app.core.security import create_access_token, generate_token, hash_password, hash_token, verify_password
from app.models.common import parse_uuid
from app.models.user import User
from app.models.user_token import UserToken
from app.repositories import business_repository, user_repository, user_token_repository
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services import email_service

VERIFY_EMAIL = "verify_email"
RESET_PASSWORD = "reset_password"


def user_to_response(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), name=user.name, email=user.email)


def enforce_rate_limit(limiter: SlidingWindowLimiter, email: str) -> None:
    if not limiter.hit(email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Too many requests. Please try again later.",
                "retryAfterSeconds": limiter.retry_after_seconds(email),
            },
        )


async def issue_user_token(db: AsyncSession, user: User, purpose: str, ttl: timedelta) -> str:
    """Invalidate earlier tokens of this purpose and return a fresh raw token."""
    await user_token_repository.invalidate_tokens_for_user(db, user.id, purpose)
    token = generate_token()
    await user_token_repository.create_token(
        db,
        UserToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(token),
            expires_at=datetime.utcnow() + ttl,
        ),
    )
    return token


async def queue_verification_email(db: AsyncSession, user: User, background_tasks: BackgroundTasks) -> None:
    token = await issue_user_token(
        db, user, VERIFY_EMAIL, timedelta(hours=settings.email_verification_expire_hours)
    )
    url = email_service.frontend_link(f"/verify-email?token={token}")
    background_tasks.add_task(email_service.send_verification_email, user.email, user.name, url)


async def invite_matches_email(db: AsyncSession, invite_token: str | None, email: str) -> bool:
    if not invite_token:
        return False
    invitation = await business_repository.find_invitation_by_token_hash(db, hash_token(invite_token))
    return bool(
        invitation
        and invitation.status == "pending"
        and invitation.expires_at > datetime.utcnow()
        and invitation.email == email
    )


async def signup(db: AsyncSession, payload: SignupRequest, background_tasks: BackgroundTasks) -> SignupResponse:
    email = payload.email.lower()
    # The invite email already proved inbox ownership, so invited signups skip verification.
    pre_verified = await invite_matches_email(db, payload.invite_token, email)
    user = User(
        name=payload.name.strip(),
        email=email,
        hashed_password=hash_password(payload.password),
        email_verified_at=datetime.utcnow() if pre_verified else None,
    )
    try:
        user_id = await user_repository.create_user(db, user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc
    created = await user_repository.find_user_by_id(db, user_id)
    if not pre_verified:
        await queue_verification_email(db, created, background_tasks)
    return SignupResponse(
        id=str(created.id),
        name=created.name,
        email=created.email,
        emailVerificationRequired=not pre_verified,
    )


async def login(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    user = await user_repository.find_user_by_email(db, payload.email.lower())
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email first",
                "email": user.email,
                "remainingAttempts": verification_resend_limiter.remaining(user.email),
            },
        )
    return TokenResponse(access_token=create_access_token(str(user.id)))


async def verify_email(db: AsyncSession, token: str) -> TokenResponse:
    user_token = await user_token_repository.find_valid_token(db, hash_token(token), VERIFY_EMAIL)
    user = await user_repository.find_user_by_id(db, user_token.user_id) if user_token else None
    if not user_token or not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_token", "message": "This verification link is invalid or has expired"},
        )
    if user.email_verified_at is None:
        user.email_verified_at = datetime.utcnow()
        db.add(user)
    await user_token_repository.invalidate_tokens_for_user(db, user.id, VERIFY_EMAIL)
    await db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


async def resend_verification(db: AsyncSession, email: str, background_tasks: BackgroundTasks) -> MessageResponse:
    email = email.lower()
    enforce_rate_limit(verification_resend_limiter, email)
    user = await user_repository.find_user_by_email(db, email)
    if user and user.email_verified_at is None:
        await queue_verification_email(db, user, background_tasks)
    return MessageResponse(
        message="If that account needs verification, a new link has been sent.",
        remainingAttempts=verification_resend_limiter.remaining(email),
    )


async def forgot_password(db: AsyncSession, email: str, background_tasks: BackgroundTasks) -> MessageResponse:
    email = email.lower()
    enforce_rate_limit(password_reset_limiter, email)
    user = await user_repository.find_user_by_email(db, email)
    if user:
        token = await issue_user_token(
            db, user, RESET_PASSWORD, timedelta(minutes=settings.password_reset_expire_minutes)
        )
        url = email_service.frontend_link(f"/reset-password?token={token}")
        background_tasks.add_task(email_service.send_password_reset_email, user.email, user.name, url)
    return MessageResponse(message="If an account exists for that email, a reset link has been sent.")


async def reset_password(db: AsyncSession, payload: ResetPasswordRequest) -> MessageResponse:
    user_token = await user_token_repository.find_valid_token(db, hash_token(payload.token), RESET_PASSWORD)
    user = await user_repository.find_user_by_id(db, user_token.user_id) if user_token else None
    if not user_token or not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_token", "message": "This reset link is invalid or has expired"},
        )
    user.hashed_password = hash_password(payload.password)
    # Receiving the reset email proves inbox ownership.
    if user.email_verified_at is None:
        user.email_verified_at = datetime.utcnow()
    db.add(user)
    await user_token_repository.invalidate_tokens_for_user(db, user.id, RESET_PASSWORD)
    await db.commit()
    return MessageResponse(message="Your password has been reset. You can log in now.")


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    try:
        parsed_id: UUID = parse_uuid(user_id, "user id")
    except HTTPException:
        return None
    return await user_repository.find_user_by_id(db, parsed_id)
