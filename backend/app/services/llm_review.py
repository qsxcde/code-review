import json
import logging
import re
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.review import MockReviewRequest, ReviewResult

logger = logging.getLogger(__name__)

LLM_ERROR_MESSAGES = {
    "authentication": "模型服务认证失败，请检查 API Key 配置",
    "bad_request": "模型服务拒绝了请求，请检查模型名称或请求参数",
    "connection": "无法连接到模型服务，请检查网络或模型服务地址",
    "rate_limit": "模型服务请求频率或额度受限，请稍后重试",
    "timeout": "模型服务请求超时，请稍后重试",
    "unavailable": "模型服务暂时不可用，请稍后重试",
    "unknown": "模型服务调用失败，请稍后重试",
}


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

        prompt = self._build_prompt()
        schema = json.dumps(ReviewResult.model_json_schema(), ensure_ascii=False)

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
            error_type = self._classify_model_error(exc)
            logger.warning(
                "llm_request_failed",
                exc_info=True,
                extra={
                    "props": {
                        "event": "llm_request_failed",
                        "model": self.model,
                        "error_type": error_type,
                        "exception_type": exc.__class__.__name__,
                        "error_message": self._sanitize_error_message(str(exc)),
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

    def _classify_model_error(self, exc: Exception) -> str:
        error_name = exc.__class__.__name__.lower()
        error_text = str(exc).lower()
        combined = f"{error_name} {error_text}"

        if "timeout" in combined or "timed out" in combined:
            return "timeout"
        if "rate_limit" in combined or "ratelimit" in combined or "429" in combined:
            return "rate_limit"
        if "authentication" in combined or "unauthorized" in combined or "401" in combined:
            return "authentication"
        if (
            "badrequest" in combined
            or "bad_request" in combined
            or "invalid request" in combined
            or "400" in combined
        ):
            return "bad_request"
        if "connection" in combined or "connect" in combined or "dns" in combined:
            return "connection"
        if "serviceunavailable" in combined or "unavailable" in combined or "503" in combined:
            return "unavailable"
        return "unknown"

    def _sanitize_error_message(self, message: str) -> str:
        return re.sub(
            r"(api[_-]?key|authorization|token)=?\S+",
            r"\1=<redacted>",
            message,
            flags=re.IGNORECASE,
        )[:300]

    def _build_prompt(self) -> Any:
        try:
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="langchain-core is not installed",
            ) from exc

        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一名资深代码审查工程师。你只分析用户提供的 PR diff，"
                    "重点关注安全、逻辑正确性、异常处理、数据一致性、并发、权限控制和测试缺失。"
                    "你的回答必须是严格 JSON，不要输出 Markdown 或额外解释。"
                    "JSON 的字段名必须保持 schema 中的英文名称，但所有字段内容必须使用中文。",
                ),
                (
                    "human",
                    "请返回一个严格符合以下 JSON Schema 的 JSON 对象：\n"
                    "{schema}\n\n"
                    "PR 数据如下：\n"
                    "{pr_payload}\n\n"
                    "规则：\n"
                    "- 只返回 JSON，不要包含 Markdown 代码块。\n"
                    "- 不要在 JSON 之外输出任何说明文字。\n"
                    "- JSON 字段名保持英文，例如 summary、risks、suggestions、metrics。\n"
                    "- JSON 字段值必须使用中文，severity、type 等枚举值按 schema 要求保持英文。\n"
                    "- 如果没有明确风险，risks 和 suggestions 返回空数组。\n"
                    "- 每个问题必须对应 diff 中的具体文件。\n"
                    "- 不要输出泛泛的代码风格建议。\n"
                    "- confidence 必须是 0 到 1 之间的数字。",
                ),
            ]
        )

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
