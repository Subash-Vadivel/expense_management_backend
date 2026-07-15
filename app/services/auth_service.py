from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.common import parse_uuid
from app.models.user import User
from app.repositories import user_repository
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from app.schemas.user import UserResponse


def user_to_response(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), name=user.name, email=user.email)


async def signup(db: AsyncSession, payload: SignupRequest) -> UserResponse:
    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
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
    return user_to_response(created)


async def login(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    user = await user_repository.find_user_by_email(db, payload.email.lower())
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(access_token=create_access_token(str(user.id)))


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    try:
        parsed_id: UUID = parse_uuid(user_id, "user id")
    except HTTPException:
        return None
    return await user_repository.find_user_by_id(db, parsed_id)
