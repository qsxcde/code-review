from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.redis import get_redis
from app.core.security import require_jwt_user
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.services.auth.service import login, register, revoke_refresh_token, rotate_tokens

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def auth_register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> AuthResponse:
    return await register(db, redis, request.email, request.password)


@router.post("/login", response_model=AuthResponse)
async def auth_login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> AuthResponse:
    return await login(db, redis, request.email, request.password)


@router.post("/refresh", response_model=AuthResponse)
async def auth_refresh(
    request: RefreshRequest,
    redis=Depends(get_redis),
) -> AuthResponse:
    return await rotate_tokens(redis, request.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def auth_logout(
    request: LogoutRequest,
    _user_id: int = Depends(require_jwt_user),
    redis=Depends(get_redis),
) -> None:
    await revoke_refresh_token(redis, request.refresh_token)
