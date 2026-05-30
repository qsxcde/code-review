import asyncio
import json
import logging
from typing import Any

from fastapi import HTTPException, status

from app.schemas.review import MockReviewRequest, ReviewResult
from app.services.llm.client import build_chat_model
from app.services.llm.errors import (
    BASE_DELAY_SECONDS,
    LLM_ERROR_MESSAGES,
    MAX_RETRIES,
    RETRIABLE_ERROR_TYPES,
    classify_model_error,
    sanitize_error_message,
)
from app.services.llm.parser import parse_review_result
from app.services.llm.payloads import build_mock_review_payload
from app.services.llm.prompt import build_review_prompt

logger = logging.getLogger(__name__)


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
        payload = build_mock_review_payload(request)
        return await self._call_llm_with_payload(payload)

    async def analyze_payload(
        self, payload: dict[str, Any], system_prompt: str | None = None
    ) -> ReviewResult:
        return await self._call_llm_with_payload(payload, system_prompt)

    async def _call_llm_with_payload(
        self, payload: dict[str, Any], system_prompt: str | None = None
    ) -> ReviewResult:
        self._ensure_model_configured()

        prompt = build_review_prompt(system_prompt)
        schema = json.dumps(ReviewResult.model_json_schema(), ensure_ascii=False)
        max_attempts = 1 + MAX_RETRIES

        for attempt in range(max_attempts):
            try:
                llm = build_chat_model(self.api_key, self.base_url, self.model)
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
                error_type = classify_model_error(exc)
                error_message = sanitize_error_message(str(exc))
                is_last = attempt == max_attempts - 1

                if error_type in RETRIABLE_ERROR_TYPES and not is_last:
                    delay = BASE_DELAY_SECONDS * (2**attempt)
                    logger.warning(
                        "llm_request_retrying",
                        extra={
                            "props": {
                                "event": "llm_request_retrying",
                                "model": self.model,
                                "attempt": attempt + 1,
                                "next_delay_s": round(delay, 1),
                                "error_type": error_type,
                                "exception_type": exc.__class__.__name__,
                                "error_message": error_message,
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
                            "error_type": error_type,
                            "exception_type": exc.__class__.__name__,
                            "error_message": error_message,
                        }
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "code": f"llm_{error_type}",
                        "message": LLM_ERROR_MESSAGES[error_type],
                    },
                ) from exc

            content = getattr(response, "content", response)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Model returned an unsupported response format",
                )

            return parse_review_result(content)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model request failed",
        )

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
