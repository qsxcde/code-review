import re

MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0
RETRIABLE_ERROR_TYPES = frozenset({"timeout", "rate_limit", "unavailable", "connection"})

LLM_ERROR_MESSAGES = {
    "authentication": "模型服务认证失败，请检查 API Key 配置",
    "bad_request": "模型服务拒绝了请求，请检查模型名称或请求参数",
    "connection": "无法连接到模型服务，请检查网络或模型服务地址",
    "rate_limit": "模型服务请求频率或额度受限，请稍后重试",
    "timeout": "模型服务请求超时，请稍后重试",
    "unavailable": "模型服务暂时不可用，请稍后重试",
    "unknown": "模型服务调用失败，请稍后重试",
}


def classify_model_error(exc: Exception) -> str:
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


def sanitize_error_message(message: str) -> str:
    return re.sub(
        r"(api[_-]?key|authorization|token)=?\S+",
        r"\1=<redacted>",
        message,
        flags=re.IGNORECASE,
    )[:300]
