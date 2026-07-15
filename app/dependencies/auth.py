from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.postgres import get_session
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.auth_service import get_user_by_id, user_to_response

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user_document(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = await get_user_by_id(db, user_id)
    if not user:
        raise credentials_exception
    return user


async def get_current_user(user: User = Depends(get_current_user_document)) -> UserResponse:
    return user_to_response(user)


async def get_current_user_id(user: User = Depends(get_current_user_document)) -> UUID:
    return user.id
