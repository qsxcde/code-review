from typing import Any

from fastapi import HTTPException, status


def build_chat_model(
    api_key: str | None,
    base_url: str | None,
    model: str | None,
) -> Any:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="langchain-openai is not installed",
        ) from exc

    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "model": model,
        "temperature": 0,
    }
    if base_url:
        kwargs["base_url"] = base_url

    return ChatOpenAI(**kwargs)
