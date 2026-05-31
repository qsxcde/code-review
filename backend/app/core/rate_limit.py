import logging
import time
from collections import defaultdict, deque
from threading import Lock
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# ── in-memory fallback ──────────────────────────────────────────────
_request_log: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()
_last_cleanup: float = time.monotonic()
_CLEANUP_INTERVAL_SECONDS = 300  # prune stale keys every 5 min


def _client_key(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{request.url.path}"


def _mem_check_and_add(key: str, limit: int, window: int) -> tuple[bool, int, int]:
    """In-memory sliding-window check.  Returns (allowed, remaining, retry_after)."""
    now = time.monotonic()
    cutoff = now - window

    global _last_cleanup
    if now - _last_cleanup > _CLEANUP_INTERVAL_SECONDS:
        _prune_stale_keys(cutoff)
        _last_cleanup = now

    with _lock:
        timestamps = _request_log[key]
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        current = len(timestamps)
        if current >= limit:
            retry_after = max(1, int(window - (now - timestamps[0])))
            return False, 0, retry_after

        timestamps.append(now)
        return True, limit - current - 1, 0


def _prune_stale_keys(cutoff: float) -> None:
    with _lock:
        stale = [k for k, q in _request_log.items() if not q or q[-1] <= cutoff]
        for k in stale:
            del _request_log[k]


# ── Redis sliding window ────────────────────────────────────────────

_REDIS_PREFIX = "rate_limit"


def _redis_key(client_key: str) -> str:
    return f"{_REDIS_PREFIX}:{client_key}"


async def _redis_check_and_add(
    redis,
    redis_key: str,
    limit: int,
    window: int,
) -> tuple[bool, int, int]:
    """Redis sorted-set sliding-window check.  Returns (allowed, remaining, retry_after)."""
    now = time.time()
    cutoff = now - window
    member = f"{now}:{uuid4().hex[:8]}"

    # 1) evict expired entries
    await redis.zremrangebyscore(redis_key, "-inf", cutoff)
    # 2) count current window
    current = await redis.zcard(redis_key)
    if current >= limit:
        # peek the oldest entry for Retry-After
        oldest = await redis.zrange(redis_key, 0, 0, withscores=True)
        if oldest:
            retry_after = max(1, int(window - (now - oldest[0][1])))
        else:
            retry_after = window
        return False, 0, retry_after
    # 3) add this request
    await redis.zadd(redis_key, {member: now})
    await redis.expire(redis_key, window + 1)
    return True, limit - current - 1, 0


# ── public dependency ───────────────────────────────────────────────

async def require_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    limit = settings.rate_limit_requests
    window = settings.rate_limit_window_seconds
    if limit <= 0 or window <= 0:
        return

    client = _client_key(request)

    # try Redis first
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        rkey = _redis_key(client)
        allowed, remaining, retry_after = await _redis_check_and_add(
            redis, rkey, limit, window,
        )
    except Exception:
        logger.debug("Redis 限流不可用，回退到内存限流", exc_info=True)
        allowed, remaining, retry_after = _mem_check_and_add(client, limit, window)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time() + retry_after)),
            },
        )
