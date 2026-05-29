import asyncio
import json
import logging
import re
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.core.exceptions import (
    LLM_ERROR_MESSAGES,
    classify_llm_error,
    sanitize_error_message,
)
from app.prompts.review import build_review_prompt
from app.schemas.review import MockReviewRequest, ReviewResult

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0
RETRIABLE_ERROR_TYPES = frozenset({"timeout", "rate_limit", "unavailable", "connection"})


class LLMReviewService:
    def __init__(
        self,
        api_key: str | None,
        base_url: str | None,
        model: str | None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    async def analyze_mock_pr(self, request: MockReviewRequest) -> ReviewResult:
        payload = self._build_review_payload(request)
        return await self._call_llm_with_payload(payload)

    async def analyze_payload(self, payload: dict[str, Any]) -> ReviewResult:
        return await self._call_llm_with_payload(payload)

    async def _call_llm_with_payload(self, payload: dict[str, Any]) -> ReviewResult:
        self._ensure_model_configured()

        prompt = build_review_prompt()
        schema = json.dumps(ReviewResult.model_json_schema(), ensure_ascii=False)
        max_attempts = 1 + MAX_RETRIES
        last_error_type = "unknown"
        last_error_message = ""

        for attempt in range(max_attempts):
            try:
                llm = self._build_llm()
                chain = prompt | llm
                response = await chain.ainvoke(
                    {
                        "schema": schema,
                        "pr_payload": json.dumps(payload, ensure_ascii=False),
                    }
                )
            except HTTPException:
                raise
            except Exception as exc:
                last_error_type = classify_llm_error(exc)
                last_error_message = sanitize_error_message(str(exc))
                is_last = attempt == max_attempts - 1

                if last_error_type in RETRIABLE_ERROR_TYPES and not is_last:
                    delay = BASE_DELAY_SECONDS * (2**attempt)
                    logger.warning(
                        "llm_request_retrying",
                        extra={
                            "props": {
                                "event": "llm_request_retrying",
                                "model": self.model,
                                "attempt": attempt + 1,
                                "next_delay_s": round(delay, 1),
                                "error_type": last_error_type,
                                "exception_type": exc.__class__.__name__,
                                "error_message": last_error_message,
                            }
                        },
                    )
                    await asyncio.sleep(delay)
                    continue

                logger.warning(
                    "llm_request_failed",
                    exc_info=True,
                    extra={
                        "props": {
                            "event": "llm_request_failed",
                            "model": self.model,
                            "attempt": attempt + 1,
                            "error_type": last_error_type,
                            "exception_type": exc.__class__.__name__,
                            "error_message": last_error_message,
                        }
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "code": f"llm_{last_error_type}",
                        "message": LLM_ERROR_MESSAGES[last_error_type],
                    },
                ) from exc

            content = getattr(response, "content", response)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Model returned an unsupported response format",
                )

            return self._parse_review_result(content)

    def _ensure_model_configured(self) -> None:
        if not self.api_key or not self.model:
            logger.error(
                "llm_config_missing",
                extra={
                    "props": {
                        "event": "llm_config_missing",
                        "has_api_key": bool(self.api_key),
                        "has_model": bool(self.model),
                    }
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OPENAI_API_KEY and OPENAI_MODEL are required for review analysis",
            )

    def _build_llm(self) -> Any:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="langchain-openai is not installed",
            ) from exc

        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "model": self.model,
            "temperature": 0,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url

        return ChatOpenAI(**kwargs)

    def _build_review_payload(self, request: MockReviewRequest) -> dict[str, Any]:
        return {
            "prUrl": str(request.pr_url),
            "title": request.title,
            "description": request.description,
            "author": request.author,
            "baseBranch": request.base_branch,
            "headBranch": request.head_branch,
            "files": [file.model_dump() for file in request.files],
        }

    def _parse_review_result(self, content: str) -> ReviewResult:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = self._extract_json_object(content)

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

    def _extract_json_object(self, content: str) -> dict[str, Any]:
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
