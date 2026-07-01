import hashlib
import json
import re

import redis.asyncio as redis

from ..config import REDIS_URL, CACHE_ENABLED, CACHE_TTL_SECONDS
from ..logging_config import get_logger

logger = get_logger(__name__)

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis | None:
    """Lazily create a single shared Redis connection pool for the process."""
    global _redis_client
    if not CACHE_ENABLED:
        return None
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _normalize_question(question: str) -> str:
    """Collapse whitespace and lowercase so trivially-different phrasing of the
    same question ("What is deadlock?" vs "what   is deadlock?") hits the
    same cache entry."""
    return re.sub(r"\s+", " ", question.strip().lower())


def build_cache_key(user_id: int, question: str, version: int) -> str:
    """Cache key versioned per-user: qa_cache:user:{id}:v{version}:{hash}.

    `version` is bumped (UserRepository.bump_cache_version) every time one of
    the user's documents is uploaded, reprocessed, or deleted. Because the
    version number is embedded directly in the key, a stale answer can never
    be served after a document changes — the old key simply stops being the
    key the application looks up, even though the old entry technically still
    sits in Redis until its TTL expires.
    """
    normalized = _normalize_question(question)
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"qa_cache:user:{user_id}:v{version}:{digest}"


class AnswerCache:
    """Thin wrapper around Redis for caching Gemini-generated answers.

    Fails open: if Redis is unavailable, every method degrades to a cache
    miss / no-op instead of raising, so the Q&A endpoint keeps working
    without caching rather than going down.
    """

    def __init__(self):
        self.client = get_redis_client()

    async def get(self, key: str) -> dict | None:
        if not self.client:
            return None
        try:
            raw = await self.client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            logger.warning("Cache read failed, falling back to live generation", exc_info=True)
            return None

    async def set(self, key: str, value: dict, ttl: int = CACHE_TTL_SECONDS) -> None:
        if not self.client:
            return
        try:
            await self.client.set(key, json.dumps(value), ex=ttl)
        except Exception:
            logger.warning("Cache write failed", exc_info=True)

    async def invalidate_user(self, user_id: int) -> None:
        """Explicitly delete every cached answer for a user (Option 1: delete
        on change). This is run any time the user's document set changes, in
        addition to bumping cache_version (Option 3: versioned keys). The two
        together mean: old keys are immediately unreachable AND eventually
        physically removed from Redis, instead of waiting around for the TTL
        (Option 2) to clean them up on its own."""
        if not self.client:
            return
        try:
            pattern = f"qa_cache:user:{user_id}:*"
            async for key in self.client.scan_iter(match=pattern):
                await self.client.delete(key)
        except Exception:
            logger.warning("Cache invalidation failed", exc_info=True)
