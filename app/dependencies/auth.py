from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.postgres import get_session
from app.models.business import BusinessEntity, BusinessMembership
from app.models.common import parse_uuid
from app.models.user import User
from app.repositories import business_repository
from app.schemas.user import UserResponse
from app.services.auth_service import get_user_by_id, user_to_response

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass(frozen=True)
class BusinessAccess:
    user: User
    business: BusinessEntity
    membership: BusinessMembership


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


async def get_business_access(
    x_business_id: str = Header(..., alias="X-Business-Id"),
    user: User = Depends(get_current_user_document),
    db: AsyncSession = Depends(get_session),
) -> BusinessAccess:
    business_id = parse_uuid(x_business_id, "business id")
    business = await business_repository.get_business(db, business_id)
    membership = await business_repository.get_membership(db, business_id, user.id)
    if not business or not membership or membership.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business access required")
    return BusinessAccess(user=user, business=business, membership=membership)


def require_business_role(*roles: str):
    async def dependency(access: BusinessAccess = Depends(get_business_access)) -> BusinessAccess:
        if access.membership.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for this business")
        return access

    return dependency
