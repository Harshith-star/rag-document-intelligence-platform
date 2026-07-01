import io
import pytest
from unittest.mock import patch

from app.services import cache_service


@pytest.mark.asyncio
@patch("app.services.qa_service.generate_answer")
@patch("app.services.qa_service.search")
@patch("app.services.document_service.add_chunks")
async def test_repeated_question_is_served_from_cache(
    mock_add_chunks, mock_search, mock_generate, client, auth_headers
):
    mock_add_chunks.return_value = 1
    mock_search.return_value = [{"text": "deadlock chunk", "filename": "os.txt", "document_id": 1}]
    mock_generate.return_value = "A deadlock is a state where processes wait on each other forever."

    await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("os.txt", io.BytesIO(b"operating systems notes"), "text/plain")},
    )

    resp1 = await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "What is deadlock?"})
    assert resp1.status_code == 200
    assert resp1.json()["cached"] is False
    assert mock_generate.call_count == 1

    resp2 = await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "  what is deadlock?  "})
    assert resp2.status_code == 200
    assert resp2.json()["cached"] is True
    assert resp2.json()["answer"] == resp1.json()["answer"]
    assert mock_generate.call_count == 1


@pytest.mark.asyncio
@patch("app.services.qa_service.generate_answer")
@patch("app.services.qa_service.search")
@patch("app.services.document_service.add_chunks")
@patch("app.services.document_service.delete_user_document")
async def test_cache_version_bumped_and_invalidated_on_new_upload(
    mock_delete_vec, mock_add_chunks, mock_search, mock_generate, client, auth_headers
):
    """Covers Option 1 (delete on change) + Option 3 (versioned keys) together:
    after a new document upload, cache_version is bumped AND old keys are
    explicitly purged, so the next identical question is guaranteed to miss
    the cache and regenerate a fresh answer."""
    mock_add_chunks.return_value = 1
    mock_search.return_value = [{"text": "chunk", "filename": "a.txt", "document_id": 1}]
    mock_generate.return_value = "first answer"

    await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("a.txt", io.BytesIO(b"content"), "text/plain")},
    )

    resp1 = await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "Explain X"})
    assert resp1.json()["cached"] is False
    assert mock_generate.call_count == 1

    resp2 = await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "Explain X"})
    assert resp2.json()["cached"] is True
    assert mock_generate.call_count == 1

    mock_generate.return_value = "second answer"
    await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("b.txt", io.BytesIO(b"more content"), "text/plain")},
    )

    resp3 = await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "Explain X"})
    assert resp3.json()["cached"] is False
    assert mock_generate.call_count == 2
    assert resp3.json()["answer"] == "second answer"


@pytest.mark.asyncio
@patch("app.services.qa_service.generate_answer")
@patch("app.services.qa_service.search")
@patch("app.services.document_service.add_chunks")
@patch("app.services.document_service.delete_user_document")
async def test_cache_invalidated_on_document_delete(
    mock_delete_vec, mock_add_chunks, mock_search, mock_generate, client, auth_headers
):
    mock_add_chunks.return_value = 1
    mock_search.return_value = [{"text": "chunk", "filename": "a.txt", "document_id": 1}]
    mock_generate.return_value = "answer v1"

    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("a.txt", io.BytesIO(b"content"), "text/plain")},
    )
    doc_id = resp.json()["id"]

    resp1 = await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "What is X?"})
    assert resp1.json()["cached"] is False

    resp2 = await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "What is X?"})
    assert resp2.json()["cached"] is True
    assert mock_generate.call_count == 1

    del_resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    mock_generate.return_value = "answer v2"
    await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("c.txt", io.BytesIO(b"new content"), "text/plain")},
    )
    resp3 = await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "What is X?"})
    assert resp3.json()["cached"] is False
    assert resp3.json()["answer"] == "answer v2"
    assert mock_generate.call_count == 2


@pytest.mark.asyncio
async def test_cache_get_set_roundtrip():
    cache = cache_service.AnswerCache()
    key = cache_service.build_cache_key(999, "hello?", 1)
    assert await cache.get(key) is None

    await cache.set(key, {"answer": "hi", "sources": ["a.txt"]}, ttl=60)
    cached = await cache.get(key)
    assert cached == {"answer": "hi", "sources": ["a.txt"]}


def test_normalize_question_collapses_whitespace_and_case():
    assert cache_service._normalize_question("  What   IS Deadlock?  ") == "what is deadlock?"


def test_build_cache_key_is_stable_for_equivalent_questions_same_version():
    k1 = cache_service.build_cache_key(1, "What is deadlock?", 3)
    k2 = cache_service.build_cache_key(1, "  what IS deadlock?  ", 3)
    assert k1 == k2


def test_build_cache_key_changes_with_version():
    k_v1 = cache_service.build_cache_key(1, "What is deadlock?", 1)
    k_v2 = cache_service.build_cache_key(1, "What is deadlock?", 2)
    assert k_v1 != k_v2
    assert ":v1:" in k_v1
    assert ":v2:" in k_v2
