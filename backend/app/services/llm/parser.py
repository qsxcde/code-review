import json
import logging
import re
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.review import ReviewResult

logger = logging.getLogger(__name__)


def parse_review_result(content: str) -> ReviewResult:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = extract_json_object(content)

    try:
        return ReviewResult.model_validate(data)
    except ValidationError as exc:
        logger.warning(
            "llm_output_schema_invalid",
            extra={
                "props": {
                    "event": "llm_output_schema_invalid",
                    "error_count": len(exc.errors()),
                }
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model output does not match ReviewResult schema",
        ) from exc


def extract_json_object(content: str) -> dict[str, Any]:
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    candidate = fenced_match.group(1) if fenced_match else content

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned invalid JSON",
        )

    try:
        data = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned invalid JSON",
        ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned invalid JSON",
        )

    return data
