import shutil
import time
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES
from ..exceptions import UnsupportedFileTypeError, FileTooLargeError, DocumentProcessingError, DocumentNotFoundError
from ..logging_config import get_logger
from ..repositories.document_repository import DocumentRepository
from ..repositories.user_repository import UserRepository
from .document_processor import process_document
from .vector_store import add_chunks, delete_user_document
from .cache_service import AnswerCache

logger = get_logger(__name__)


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.repo = DocumentRepository(db)
        self.user_repo = UserRepository(db)
        self.cache = AnswerCache()

    async def _invalidate_cache_for_document_change(self, user_id: int) -> None:
        """The Option 1 + Option 3 combo, run any time a document is added,
        reprocessed, or removed:
          1. Bump the user's cache_version (DB) — every previously-built cache
             key embeds the old version number, so it instantly stops being
             the key the app looks up (versioned keys).
          2. Explicitly delete the old keys from Redis (delete-on-change)
             instead of waiting for their TTL to expire, so Redis memory
             doesn't accumulate orphaned entries.
        """
        new_version = await self.user_repo.bump_cache_version(user_id)
        await self.cache.invalidate_user(user_id)
        logger.info("Cache invalidated user_id=%s new_cache_version=%s", user_id, new_version)

    async def upload(self, user: models.User, file: UploadFile) -> models.Document:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")

        user_dir = UPLOAD_DIR / str(user.id)
        user_dir.mkdir(parents=True, exist_ok=True)
        dest_path = user_dir / file.filename

        size = 0
        with dest_path.open("wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()
                    dest_path.unlink(missing_ok=True)
                    raise FileTooLargeError()
                buffer.write(chunk)

        logger.info("Upload started user_id=%s filename=%s size=%s", user.id, file.filename, size)
        doc = await self.repo.create(user.id, file.filename, size, suffix)

        start = time.perf_counter()
        try:
            # New document version: extract -> chunk -> re-embed -> rebuild FAISS.
            chunks = process_document(dest_path)
            num_added = add_chunks(user.id, doc.id, file.filename, chunks)
            elapsed = time.perf_counter() - start
            doc = await self.repo.mark_completed(doc, num_added, elapsed)
            logger.info(
                "Upload completed user_id=%s document_id=%s chunks=%s time=%.2fs",
                user.id, doc.id, num_added, elapsed,
            )

            # Document content changed -> any cached answers may now be stale.
            await self._invalidate_cache_for_document_change(user.id)
        except Exception as exc:
            await self.repo.mark_failed(doc)
            logger.exception("Document processing failed user_id=%s document_id=%s", user.id, doc.id)
            raise DocumentProcessingError(f"Failed to process document: {exc}")

        return doc

    async def list_documents(self, user: models.User, page: int, limit: int, search: str | None):
        return await self.repo.list_for_user(user.id, page, limit, search)

    async def get_stats(self, user: models.User) -> dict:
        return await self.repo.get_stats(user.id)

    async def rename(self, user: models.User, doc_id: int, new_filename: str) -> models.Document:
        doc = await self.repo.get_by_id(doc_id, user.id)
        if not doc:
            raise DocumentNotFoundError()
        doc = await self.repo.rename(doc, new_filename)
        logger.info("Document renamed user_id=%s document_id=%s new_name=%s", user.id, doc_id, new_filename)
        # Filename changes don't affect content/answers, but sources returned
        # by /qa/ask include filenames, so refresh those too for consistency.
        await self._invalidate_cache_for_document_change(user.id)
        return doc

    async def delete(self, user: models.User, doc_id: int) -> None:
        doc = await self.repo.get_by_id(doc_id, user.id)
        if not doc:
            raise DocumentNotFoundError()
        file_path = UPLOAD_DIR / str(user.id) / doc.filename
        if file_path.exists():
            file_path.unlink()

        # Delete old FAISS vectors for this document before removing the row.
        delete_user_document(user.id, doc.id)
        await self.repo.delete(doc)

        # Document set changed -> invalidate every cached answer for this user.
        await self._invalidate_cache_for_document_change(user.id)
        logger.info("Document deleted user_id=%s document_id=%s", user.id, doc_id)
