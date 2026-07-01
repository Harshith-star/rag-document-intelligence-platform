from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, auth
from ..database import get_db
from ..exceptions import DocumentNotFoundError
from ..services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=schemas.DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await DocumentService(db).upload(current_user, file)


@router.get("/", response_model=schemas.DocumentListOut)
async def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await DocumentService(db).list_documents(current_user, page, limit, search)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.patch("/{document_id}", response_model=schemas.DocumentOut)
async def rename_document(
    document_id: int,
    payload: schemas.DocumentRename,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await DocumentService(db).rename(current_user, document_id, payload.filename)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await DocumentService(db).delete(current_user, document_id)
