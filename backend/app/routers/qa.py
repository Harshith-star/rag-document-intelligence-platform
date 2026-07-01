from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, auth
from ..database import get_db
from ..services.qa_service import QAService

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=schemas.AnswerResponse)
async def ask_question(
    payload: schemas.QuestionRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await QAService(db).ask(current_user, payload.question)
