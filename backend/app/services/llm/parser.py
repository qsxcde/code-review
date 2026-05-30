import json
import logging
import re
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.review import ReviewResult
from app.services.llm.errors import preview_model_content

logger = logging.getLogger(__name__)


def parse_review_result(content: str, stage: str | None = None, model: str | None = None) -> ReviewResult:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = extract_json_object(content, stage=stage, model=model)

    try:
        return ReviewResult.model_validate(data)
    except ValidationError as exc:
        preview = preview_model_content(content)
        logger.warning(
            "llm_output_schema_invalid",
            extra={
                "props": {
                    "event": "llm_output_schema_invalid",
                    "stage": stage,
                    "model": model,
                    "error_count": len(exc.errors()),
                    "content_preview": preview,
                }
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "llm_schema_invalid",
                "message": "模型返回内容不符合 ReviewResult 结构",
                "stage": stage,
                "model": model,
                "error_count": len(exc.errors()),
                "content_preview": preview,
            },
        ) from exc


def parse_json_object(content: str, stage: str | None = None, model: str | None = None) -> dict[str, Any]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = extract_json_object(content, stage=stage, model=model)

    if not isinstance(data, dict):
        _log_invalid_json(content, stage, model)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "llm_invalid_json",
                "message": "模型返回 JSON 不是对象结构",
                "stage": stage,
                "model": model,
                "content_preview": preview_model_content(content),
            },
        )

    return data


def extract_json_object(content: str, stage: str | None = None, model: str | None = None) -> dict[str, Any]:
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    candidate = fenced_match.group(1) if fenced_match else content

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        _log_invalid_json(content, stage, model)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "llm_invalid_json",
                "message": "模型返回内容不是合法 JSON",
                "stage": stage,
                "model": model,
                "content_preview": preview_model_content(content),
            },
        )

    try:
        data = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as exc:
        _log_invalid_json(content, stage, model)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "llm_invalid_json",
                "message": "模型返回内容不是合法 JSON",
                "stage": stage,
                "model": model,
                "content_preview": preview_model_content(content),
            },
        ) from exc

    if not isinstance(data, dict):
        _log_invalid_json(content, stage, model)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "llm_invalid_json",
                "message": "模型返回 JSON 不是对象结构",
                "stage": stage,
                "model": model,
                "content_preview": preview_model_content(content),
            },
        )

    return data


def _log_invalid_json(content: str, stage: str | None, model: str | None) -> None:
    logger.warning(
        "llm_output_json_invalid",
        extra={
            "props": {
                "event": "llm_output_json_invalid",
                "stage": stage,
                "model": model,
                "content_preview": preview_model_content(content),
            }
        },
    )
