import asyncio
import logging

import bcrypt
import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import AuthResponse, UserOut
from app.services.auth.jwt import (
    REFRESH_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    extract_jti_payload,
)

logger = logging.getLogger(__name__)

EMAIL_EXISTS_ERRNO = 1062
BCRYPT_ROUNDS = 12


def _validate_password_strength(password: str) -> None:
    if not any(c.isalpha() for c in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one letter",
        )
    if not any(c.isdigit() for c in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one digit",
        )


async def _hash_password(password: str) -> str:
    loop = asyncio.get_running_loop()
    hashed = await loop.run_in_executor(
        None,
        lambda: bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(BCRYPT_ROUNDS)),
    )
    return hashed.decode("utf-8")


async def _verify_password(password: str, password_hash: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")),
    )


async def register(
    db: AsyncSession,
    redis: aioredis.Redis,
    email: str,
    password: str,
) -> AuthResponse:
    _validate_password_strength(password)
    password_hash = await _hash_password(password)

    user = User(email=email, password_hash=password_hash)
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        if exc.orig and getattr(exc.orig, "args", [None])[0] == EMAIL_EXISTS_ERRNO:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        logger.exception("Unexpected integrity error during registration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)
    jti, payload = extract_jti_payload(refresh_token)
    expire_seconds = payload["exp"] - payload["iat"]
    await redis.setex(
        f"refresh:{user.id}:{jti}",
        expire_seconds,
        "valid",
    )

    return AuthResponse(
        user=UserOut(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
        ),
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def login(
    db: AsyncSession,
    redis: aioredis.Redis,
    email: str,
    password: str,
) -> AuthResponse:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not await _verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)
    jti, payload = extract_jti_payload(refresh_token)
    expire_seconds = payload["exp"] - payload["iat"]
    await redis.setex(
        f"refresh:{user.id}:{jti}",
        expire_seconds,
        "valid",
    )

    return AuthResponse(
        user=UserOut(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
        ),
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def rotate_tokens(
    redis: aioredis.Redis,
    refresh_token_str: str,
) -> AuthResponse:
    from jwt import ExpiredSignatureError, InvalidTokenError

    try:
        payload = decode_token(refresh_token_str, REFRESH_TYPE)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = int(payload["sub"])
    jti = payload["jti"]
    redis_key = f"refresh:{user_id}:{jti}"

    exists = await redis.exists(redis_key)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    await redis.delete(redis_key)

    email = payload.get("email", "")
    new_access_token = create_access_token(user_id, email)
    new_refresh_token = create_refresh_token(user_id, email)
    new_jti, new_payload = extract_jti_payload(new_refresh_token)
    expire_seconds = new_payload["exp"] - new_payload["iat"]
    await redis.setex(
        f"refresh:{user_id}:{new_jti}",
        expire_seconds,
        "valid",
    )

    return AuthResponse(
        user=UserOut(id=user_id, email=email, created_at=payload.get("iat", "")),
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


async def revoke_refresh_token(
    redis: aioredis.Redis,
    refresh_token_str: str,
) -> None:
    from jwt import InvalidTokenError

    try:
        jti, payload = extract_jti_payload(refresh_token_str)
    except InvalidTokenError:
        return

    user_id = payload.get("sub", "")
    redis_key = f"refresh:{user_id}:{jti}"
    await redis.delete(redis_key)
