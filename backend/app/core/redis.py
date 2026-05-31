import logging

import redis.asyncio as aioredis
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
        except Exception as exc:
            logger.warning("Redis 连接失败，无法创建连接 | error=%s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service is unavailable, please try again later",
            ) from exc
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
