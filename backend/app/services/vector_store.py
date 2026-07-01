import json
import faiss
import numpy as np
from pathlib import Path

from ..config import VECTOR_DIR
from .gemini_service import embed_texts, embed_query


def _paths(user_id: int):
    user_dir = VECTOR_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "index.faiss", user_dir / "meta.json"


def _load_meta(meta_path: Path) -> list[dict]:
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    return []


def add_chunks(user_id: int, document_id: int, filename: str, chunks: list[str]) -> int:
    if not chunks:
        return 0
    index_path, meta_path = _paths(user_id)
    vectors = np.array(embed_texts(chunks), dtype="float32")
    dim = vectors.shape[1]

    if index_path.exists():
        index = faiss.read_index(str(index_path))
    else:
        index = faiss.IndexFlatL2(dim)

    index.add(vectors)
    faiss.write_index(index, str(index_path))

    meta = _load_meta(meta_path)
    for chunk in chunks:
        meta.append({"document_id": document_id, "filename": filename, "text": chunk})
    meta_path.write_text(json.dumps(meta))

    return len(chunks)


def search(user_id: int, query: str, top_k: int = 4) -> list[dict]:
    index_path, meta_path = _paths(user_id)
    if not index_path.exists():
        return []
    index = faiss.read_index(str(index_path))
    meta = _load_meta(meta_path)

    query_vec = np.array([embed_query(query)], dtype="float32")
    k = min(top_k, index.ntotal)
    if k == 0:
        return []
    distances, indices = index.search(query_vec, k)

    results = []
    for idx in indices[0]:
        if 0 <= idx < len(meta):
            results.append(meta[idx])
    return results


def delete_user_document(user_id: int, document_id: int) -> None:
    """Rebuild the user's FAISS index excluding chunks from the given document.

    FAISS's flat index doesn't support in-place deletion by id easily across
    versions, so we rebuild from the remaining metadata. Fine for the index
    sizes this app expects (per-user, modest document counts).
    """
    index_path, meta_path = _paths(user_id)
    if not meta_path.exists():
        return
    meta = _load_meta(meta_path)
    remaining = [m for m in meta if m["document_id"] != document_id]

    if not remaining:
        index_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        return

    vectors = np.array(embed_texts([m["text"] for m in remaining]), dtype="float32")
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)
    faiss.write_index(index, str(index_path))
    meta_path.write_text(json.dumps(remaining))
