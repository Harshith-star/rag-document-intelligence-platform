"""QueryLogRepository — stores and retrieves Q&A history + stats."""
import json
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models


class QueryLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        owner_id: int,
        question: str,
        response_time: float,
        was_cached: bool = False,
    ) -> models.QueryLog:
        entry = models.QueryLog(
            owner_id=owner_id,
            question=question,
            response_time=response_time,
            was_cached=1 if was_cached else 0,
        )
        self._db.add(entry)
        await self._db.commit()
        await self._db.refresh(entry)
        return entry

    async def get_stats(self, owner_id: int) -> dict:
        result = await self._db.execute(
            select(
                func.count(models.QueryLog.id),
                func.coalesce(func.sum(models.QueryLog.was_cached), 0),
                func.coalesce(func.avg(models.QueryLog.response_time), 0.0),
            ).where(models.QueryLog.owner_id == owner_id)
        )
        total, cache_hits, avg_time = result.one()
        return {
            "questions_asked": int(total),
            "cache_hits": int(cache_hits),
            "avg_response_time_seconds": round(float(avg_time), 3),
        }

    async def get_recent(self, owner_id: int, limit: int = 5) -> list[dict]:
        result = await self._db.execute(
            select(
                models.QueryLog.question,
                models.QueryLog.was_cached,
                models.QueryLog.created_at,
            )
            .where(models.QueryLog.owner_id == owner_id)
            .order_by(models.QueryLog.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "question": row.question,
                "was_cached": bool(row.was_cached),
                "created_at": row.created_at.isoformat(),
            }
            for row in result.all()
        ]
