import asyncio
import json
import logging
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.review import MockReviewRequest, ReviewResult
from app.services.llm.client import build_chat_model
from app.services.llm.errors import (
    BASE_DELAY_SECONDS,
    LLM_ERROR_MESSAGES,
    MAX_RETRIES,
    RETRIABLE_ERROR_TYPES,
    classify_model_error,
    preview_model_content,
    sanitize_error_message,
)
from app.services.llm.parser import parse_json_object, parse_review_result
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
        self,
        payload: dict[str, Any],
        system_prompt: str | None = None,
        stage: str | None = None,
    ) -> ReviewResult:
        return await self._call_llm_with_payload(payload, system_prompt, stage=stage)

    async def analyze_json_payload(
        self,
        payload: dict[str, Any],
        system_prompt: str,
        stage: str | None = None,
    ) -> dict[str, Any]:
        return await self._call_llm_with_payload(
            payload,
            system_prompt,
            stage=stage,
            parse_as="json",
        )

    async def _call_llm_with_payload(
        self,
        payload: dict[str, Any],
        system_prompt: str | None = None,
        stage: str | None = None,
        parse_as: str = "review_result",
    ) -> ReviewResult | dict[str, Any]:
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
                        "LLM调用重试",
                        extra={
                            "props": {
                                "stage": stage,
                                "model": self.model,
                                "attempt": attempt + 1,
                                "delay_s": delay,
                                "error": error_type,
                                "error_message": error_message,
                            }
                        },
                    )
                    await asyncio.sleep(delay)
                    continue

                logger.warning(
                    "LLM调用失败",
                    exc_info=True,
                    extra={
                        "props": {
                            "stage": stage,
                            "model": self.model,
                            "attempt": attempt + 1,
                            "error": error_type,
                            "error_message": error_message,
                        }
                    },
                )
                detail: dict = {
                    "code": f"llm_{error_type}",
                    "message": LLM_ERROR_MESSAGES[error_type],
                }
                if settings.debug:
                    detail.update({
                        "stage": stage,
                        "model": self.model,
                        "error_type": error_type,
                        "error_message": error_message,
                    })
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=detail,
                ) from exc

            content = getattr(response, "content", response)
            if not isinstance(content, str):
                logger.warning(
                    "llm_response_format_unsupported",
                    extra={
                        "props": {
                            "event": "llm_response_format_unsupported",
                            "stage": stage,
                            "model": self.model,
                            "response_type": type(content).__name__,
                        }
                    },
                )
                format_detail: dict = {
                    "code": "llm_response_format_unsupported",
                    "message": "模型返回了不支持的响应格式",
                }
                if settings.debug:
                    format_detail.update({
                        "stage": stage,
                        "model": self.model,
                        "response_type": type(content).__name__,
                    })
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=format_detail,
                )

            try:
                if parse_as == "json":
                    return parse_json_object(content, stage=stage, model=self.model)
                return parse_review_result(content, stage=stage, model=self.model)
            except HTTPException as exc:
                logger.warning(
                    "LLM输出解析失败",
                    exc_info=True,
                    extra={
                        "props": {
                            "stage": stage,
                            "model": self.model,
                            "content_preview": preview_model_content(content),
                            "detail": exc.detail,
                        }
                    },
                )
                raise

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
