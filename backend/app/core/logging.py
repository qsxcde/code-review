import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


APP_LOGGERS = (
    "app",
    "uvicorn.error",
    "uvicorn.access",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        props = getattr(record, "props", None)
        if isinstance(props, dict):
            payload.update(props)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        module = record.name
        props = getattr(record, "props", None)
        suffix = ""

        if isinstance(props, dict) and props:
            suffix = " | " + " ".join(f"{key}={value}" for key, value in props.items())

        message = (
            f"{timestamp} {record.levelname:<7} [{module}] "
            f"{record.getMessage()}{suffix}"
        )

        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def _normalize_level(level: str) -> int:
    value = getattr(logging, level.upper(), logging.INFO)
    return value if isinstance(value, int) else logging.INFO


def _build_handler(log_format: str) -> logging.Handler:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(TextFormatter() if log_format == "dev" else JsonFormatter())
    return handler


def configure_logging(log_level: str, log_format: str = "json") -> None:
    level = _normalize_level(log_level)
    handler = _build_handler(log_format)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in APP_LOGGERS:
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
        logger.disabled = False

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)

    logging.getLogger("app").info(
        "Logging configured",
        extra={
            "props": {
                "level": logging.getLevelName(level),
                "format": log_format,
            }
        },
    )
