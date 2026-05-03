from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.dependencies.auth import get_current_user
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter()


@router.post("/signup", response_model=UserResponse, status_code=201)
async def signup(payload: SignupRequest, db: AsyncIOMotorDatabase = Depends(get_database)) -> UserResponse:
    return await auth_service.signup(db, payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_database)) -> TokenResponse:
    return await auth_service.login(db, payload)


@router.get("/me", response_model=UserResponse)
async def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
