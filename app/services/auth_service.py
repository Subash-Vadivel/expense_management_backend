from __future__ import annotations

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import UserModel
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from app.schemas.user import UserResponse


def user_to_response(user: dict) -> UserResponse:
    return UserResponse(id=str(user["_id"]), name=user["name"], email=user["email"])


async def signup(db: AsyncIOMotorDatabase, payload: SignupRequest) -> UserResponse:
    user = UserModel(
        name=payload.name.strip(),
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
    )
    try:
        result = await db.users.insert_one(user.to_mongo())
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc
    created = await db.users.find_one({"_id": result.inserted_id})
    return user_to_response(created)


async def login(db: AsyncIOMotorDatabase, payload: LoginRequest) -> TokenResponse:
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(access_token=create_access_token(str(user["_id"])))


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    if not ObjectId.is_valid(user_id):
        return None
    return await db.users.find_one({"_id": ObjectId(user_id)})
