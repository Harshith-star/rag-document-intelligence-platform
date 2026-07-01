from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, owner_id: int, filename: str, file_size: int, file_type: str) -> models.Document:
        doc = models.Document(
            owner_id=owner_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            processing_status=models.ProcessingStatus.PENDING,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def mark_completed(self, doc: models.Document, num_chunks: int, processing_time: float) -> models.Document:
        doc.num_chunks = num_chunks
        doc.processing_time = processing_time
        doc.processing_status = models.ProcessingStatus.COMPLETED
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def mark_failed(self, doc: models.Document) -> models.Document:
        doc.processing_status = models.ProcessingStatus.FAILED
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def get_by_id(self, doc_id: int, owner_id: int) -> models.Document | None:
        result = await self.db.execute(
            select(models.Document).where(models.Document.id == doc_id, models.Document.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, owner_id: int, page: int = 1, limit: int = 20, search: str | None = None
    ) -> tuple[list[models.Document], int]:
        query = select(models.Document).where(models.Document.owner_id == owner_id)
        count_query = select(func.count()).select_from(models.Document).where(models.Document.owner_id == owner_id)

        if search:
            pattern = f"%{search}%"
            query = query.where(models.Document.filename.ilike(pattern))
            count_query = count_query.where(models.Document.filename.ilike(pattern))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(models.Document.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def rename(self, doc: models.Document, new_filename: str) -> models.Document:
        doc.filename = new_filename
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def delete(self, doc: models.Document) -> None:
        await self.db.delete(doc)
        await self.db.commit()

    async def get_stats(self, owner_id: int) -> dict:
        result = await self.db.execute(
            select(func.count(models.Document.id), func.coalesce(func.sum(models.Document.file_size), 0))
            .where(models.Document.owner_id == owner_id)
        )
        total_docs, total_size = result.one()
        return {"total_documents": total_docs, "storage_used_bytes": int(total_size)}
