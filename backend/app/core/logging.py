import logging
import sys
from datetime import datetime, timezone
from typing import Any

import colorama

colorama.init()


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        props = getattr(record, "props", None)
        if isinstance(props, dict):
            payload.update(props)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return self._json_dumps(payload)

    @staticmethod
    def _json_dumps(payload: dict[str, Any]) -> str:
        import json
        return json.dumps(payload, ensure_ascii=False)


class DevLogFormatter(logging.Formatter):
    COLORS = {
        "ERROR": colorama.Fore.RED,
        "WARNING": colorama.Fore.YELLOW,
        "INFO": colorama.Fore.RESET,
        "DEBUG": colorama.Fore.LIGHTBLACK_EX,
    }

    def format(self, record: logging.LogRecord) -> str:
        ts = (
            datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            + f".{int(record.msecs):03d}"
        )
        color = self.COLORS.get(record.levelname, "")
        reset = colorama.Style.RESET_ALL

        parts = record.name.split(".")
        module = ".".join(parts[-2:]) if len(parts) >= 2 else record.name
        module = module.ljust(20)

        message = record.getMessage()

        props = getattr(record, "props", None)
        extra_str = ""
        if isinstance(props, dict):
            extra_parts = []
            for k, v in props.items():
                if k == "event":
                    continue
                if isinstance(v, float):
                    extra_parts.append(f"{k}={v:.1f}")
                else:
                    extra_parts.append(f"{k}={v}")
            if extra_parts:
                extra_str = " | " + " ".join(extra_parts)

        line = f"{ts} {color}{record.levelname:<5}{reset} [{module}] {message}{extra_str}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line


def configure_logging(log_level: str, log_format: str = "json") -> None:
    handler = logging.StreamHandler(sys.stdout)

    if log_format == "dev":
        handler.setFormatter(DevLogFormatter())
    else:
        handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
