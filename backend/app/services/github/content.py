"""GitHub Contents API helpers."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 200 * 1024
MAX_FETCH_FILES = 20


async def fetch_full_content(
    client, owner: str, repo: str, path: str, ref: str
) -> Optional[str]:
    """Fetch full file content. Returns None if file is too large or API fails."""
    try:
        content = await client.get_file_content(owner, repo, path, ref)
        if content is None:
            return None
        if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
            logger.debug("File %s exceeds size limit, skipping full content", path)
            return None
        return content
    except Exception as exc:
        logger.debug("Failed to fetch full content for %s: %s", path, exc)
        return None
