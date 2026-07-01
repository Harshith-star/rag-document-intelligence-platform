"""QAService — grounded Q&A with Redis caching (versioned keys + explicit purge)."""
import time

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import TOP_K
from ..exceptions import NoDocumentsError, GenerationError
from ..logging_config import get_logger
from ..models import User
from ..repositories.query_log_repository import QueryLogRepository
from ..repositories.user_repository import UserRepository
from .cache_service import AnswerCache, build_cache_key
from .vector_store import search
from .gemini_service import generate_answer

logger = get_logger(__name__)

_SYSTEM = (
    "You are a precise research assistant. Answer the question using ONLY the context "
    "provided. If the context does not contain enough information, say so clearly. "
    "Always cite the source filename at the end of your answer."
)


class QAService:
    def __init__(self, db: AsyncSession) -> None:
        self._user_repo  = UserRepository(db)
        self._query_repo = QueryLogRepository(db)
        self._cache      = AnswerCache()

    async def ask(self, user: User, question: str) -> dict:
        start = time.perf_counter()

        # Always re-read cache_version from DB — the `user` object was loaded
        # at JWT auth time and may pre-date a concurrent doc upload/delete.
        current = await self._user_repo.get_by_id(user.id)
        key     = build_cache_key(user.id, question, current.cache_version)

        cached = await self._cache.get(key)
        if cached is not None:
            elapsed = round(time.perf_counter() - start, 4)
            await self._query_repo.log(user.id, question, elapsed, was_cached=True)
            logger.info("Cache HIT user_id=%s v=%s", user.id, current.cache_version)
            return {**cached, "cached": True}

        # FAISS retrieval
        results = search(user.id, question, top_k=TOP_K)
        if not results:
            raise NoDocumentsError()

        context = "\n\n---\n\n".join(
            f"[{r['filename']}]\n{r['text']}" for r in results
        )
        sources = sorted({r["filename"] for r in results})

        # Gemini generation
        try:
            answer = generate_answer(question, context, _SYSTEM)
        except RuntimeError as exc:
            raise GenerationError(str(exc)) from exc

        payload = {"answer": answer, "sources": sources}
        await self._cache.set(key, payload)

        elapsed = round(time.perf_counter() - start, 3)
        await self._query_repo.log(user.id, question, elapsed, was_cached=False)
        logger.info("QA MISS user_id=%s v=%s time=%.3fs", user.id, current.cache_version, elapsed)
        return {**payload, "cached": False}

    async def get_stats(self, user: User) -> dict:
        return await self._query_repo.get_stats(user.id)
