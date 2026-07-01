"""Dashboard router — aggregated analytics for the frontend analytics tab."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from .. import models, schemas, auth
from ..database import get_db
from ..services.document_service import DocumentService
from ..services.qa_service import QAService
from ..repositories.query_log_repository import QueryLogRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=schemas.DashboardStats)
async def get_stats(
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc_stats  = await DocumentService(db).get_stats(current_user)
    qa_stats   = await QAService(db).get_stats(current_user)

    # Recent questions for the analytics history panel
    query_repo = QueryLogRepository(db)
    recent     = await query_repo.get_recent(current_user.id, limit=5)

    return {
        **doc_stats,
        **qa_stats,
        "recent_questions": recent,
    }
