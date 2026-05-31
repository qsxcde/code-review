from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings

ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"
ALGORITHM = "HS256"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int, email: str) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": ACCESS_TYPE,
        "jti": uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, email: str) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": REFRESH_TYPE,
        "jti": uuid4().hex,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise
    except InvalidTokenError as exc:
        raise InvalidTokenError("Invalid token") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(
            f"Expected token type '{expected_type}', got '{payload.get('type')}'"
        )

    return payload


def extract_jti_payload(token: str) -> tuple[str, dict]:
    """Extract jti and payload from a token without verifying expiry (for logout)."""
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[ALGORITHM],
        options={"verify_exp": False},
    )
    jti = payload.get("jti")
    if not jti:
        raise InvalidTokenError("Token missing jti")
    return jti, payload
