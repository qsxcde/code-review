"""SSE endpoint for streaming review progress."""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.redis import get_redis
from app.core.security import require_jwt_user
from app.models.review_record import ReviewRecord
from app.services.review.record_service import get_user_record

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review_progress"])


@router.get("/analyze/{record_id}/stream")
async def stream_progress(
    record_id: int,
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    record = await get_user_record(db, record_id, user_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review record not found"
        )

    if record.status in ("completed", "failed"):
        return _immediate_response(record)

    async def event_stream():
        pubsub = redis.pubsub()
        try:
            await pubsub.subscribe(f"progress:{record_id}")
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                yield f"data: {data}\n\n"
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if event.get("event") in ("complete", "error"):
                    break
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(f"progress:{record_id}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _immediate_response(record: ReviewRecord) -> StreamingResponse:
    payload = json.dumps(
        {
            "event": "complete",
            "status": record.status,
            "record_id": record.id,
            "percent": 100,
        },
        ensure_ascii=False,
    )

    async def single_event():
        yield f"data: {payload}\n\n"

    return StreamingResponse(single_event(), media_type="text/event-stream")
