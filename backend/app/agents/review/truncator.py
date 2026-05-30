"""Smart content truncation at function/class/method boundaries."""
import re
import logging

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 4000

BOUNDARY_PATTERNS = {
    "py": r"\n(def |class |async def )",
    "js": r"\n(function |class |export |const .+=.*=>)",
    "ts": r"\n(function |class |export |interface |type |const .+=.*=>)",
    "java": r"\n(\s*public |\s*private |\s*protected |\s*class |\s*interface )",
    "go": r"\n(func |type )",
    "sql": r"\n(CREATE |ALTER |DROP |INSERT |SELECT |WITH )",
}

FALLBACK_PATTERN = r"\n\S"


def _find_boundary(content: str, max_pos: int, language: str) -> int:
    pattern = BOUNDARY_PATTERNS.get(language, FALLBACK_PATTERN)
    matches = list(re.finditer(pattern, content[:max_pos]))
    if not matches:
        return max_pos
    return matches[-1].start()


def smart_truncate(content: str, max_chars: int = MAX_CONTENT_CHARS, language: str = "") -> str:
    """Truncate content at the nearest function/class/type boundary."""
    if len(content) <= max_chars:
        return content

    boundary = _find_boundary(content, max_chars, language)
    if boundary < max_chars // 2:
        return content[:max_chars] + "\n# ... (truncated)"

    return content[:boundary] + "\n# ... (truncated)"


def detect_language(filename: str) -> str:
    """Map filename extension to language key for boundary patterns."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    lang_map = {
        "py": "py", "js": "js", "ts": "ts", "tsx": "ts", "jsx": "js",
        "java": "java", "go": "go", "sql": "sql",
    }
    return lang_map.get(ext, "")
