"""Multi-language import/require/include parsing."""
import re
import logging

logger = logging.getLogger(__name__)

STD_LIBS = {
    "py": {"os", "sys", "json", "re", "time", "datetime", "logging", "collections",
           "typing", "pathlib", "io", "math", "functools", "itertools", "abc",
           "asyncio", "unittest", "subprocess", "hashlib", "urllib", "http"},
    "js": {"fs", "path", "http", "https", "url", "crypto", "stream", "events",
           "util", "buffer", "os", "child_process", "assert"},
    "go": {"fmt", "io", "os", "time", "strings", "strconv", "errors", "sync",
           "context", "net", "http", "log", "encoding", "math", "sort"},
}

IMPORT_PATTERNS = {
    "py": r"^(?:from|import)\s+([\w.]+)",
    "js": r'(?:import\s+.*?\s+from\s+|require\()[\x22\x27]([^\x22\x27]+)',
    "ts": r'(?:import\s+.*?\s+from\s+|require\()[\x22\x27]([^\x22\x27]+)',
    "go": r"\"([^\"]+)\"",
    "java": r"^import\s+([\w.]+)",
}

MAX_IMPORTS = 20


def _is_stdlib(module: str, language: str) -> bool:
    libs = STD_LIBS.get(language, set())
    top = module.split(".")[0]
    return top in libs


def _is_relative_import(module: str) -> bool:
    return module.startswith(".") and not module.startswith("..")


def parse_imports(content: str, language: str) -> list[str]:
    """Parse local/repo imports from source content. Filters out stdlib and third-party."""
    pattern = IMPORT_PATTERNS.get(language)
    if not pattern:
        return []

    results = []
    try:
        for line in content.split("\n"):
            match = re.match(pattern, line.strip())
            if not match:
                continue
            module = match.group(1)
            if _is_stdlib(module, language):
                continue
            if language == "go":
                if not module.startswith(("github.com/", "gitlab.com/", ".")):
                    continue
            elif language in ("js", "ts"):
                if not (module.startswith("./") or module.startswith("../") or module.startswith("@/")):
                    continue
            elif language == "java":
                if not module.startswith(("com.", "org.", "net.")):
                    continue
            elif language == "py":
                if not (_is_relative_import(module) or "." in module):
                    if module.split(".")[0] == module:
                        continue
            results.append(module)
            if len(results) >= MAX_IMPORTS:
                break
    except Exception as exc:
        logger.debug("Import parsing failed: %s", exc)

    return list(dict.fromkeys(results))  # dedup preserving order
