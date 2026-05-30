"""Publish review progress events via Redis pub/sub."""
import json
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


async def publish_progress(
    redis: aioredis.Redis, record_id: int, event: str, **kwargs
) -> None:
    payload = {"event": event}
    payload.update(kwargs)
    try:
        await redis.publish(
            f"progress:{record_id}", json.dumps(payload, ensure_ascii=False)
        )
    except Exception:
        logger.warning("Redis pub/sub 发布失败 | record_id=%d event=%s", record_id, event)


async def publish_phase_start(
    redis: aioredis.Redis, record_id: int, phase: str, message: str, percent: int
) -> None:
    await publish_progress(
        redis, record_id, "phase_start", phase=phase, message=message, percent=percent
    )


async def publish_phase_done(
    redis: aioredis.Redis, record_id: int, phase: str, percent: int
) -> None:
    await publish_progress(
        redis, record_id, "phase_done", phase=phase, percent=percent
    )


async def publish_agent_start(
    redis: aioredis.Redis, record_id: int, agent: str, message: str, percent: int
) -> None:
    await publish_progress(
        redis, record_id, "agent_start", agent=agent, message=message, percent=percent
    )


async def publish_agent_done(
    redis: aioredis.Redis, record_id: int, agent: str, risks: int, high: int, percent: int
) -> None:
    await publish_progress(
        redis, record_id, "agent_done", agent=agent, risks=risks, high=high, percent=percent
    )


async def publish_complete(
    redis: aioredis.Redis, record_id: int, summary: dict | None = None
) -> None:
    await publish_progress(
        redis, record_id, "complete", status="completed", review_record_id=record_id,
        percent=100, summary=summary,
    )


async def publish_error(
    redis: aioredis.Redis, record_id: int, agent: str, message: str, percent: int
) -> None:
    await publish_progress(
        redis, record_id, "error", status="failed", agent=agent,
        message=message, percent=percent,
    )
