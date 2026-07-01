import io
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_upload_requires_auth(client):
    resp = await client.post("/api/v1/documents/upload", files={"file": ("a.txt", io.BytesIO(b"hi"), "text/plain")})
    assert resp.status_code == 401


@pytest.mark.asyncio
@patch("app.services.document_service.add_chunks")
async def test_upload_document(mock_add_chunks, client, auth_headers):
    mock_add_chunks.return_value = 1
    content = b"This is a test document about cats and dogs."
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("notes.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "notes.txt"
    assert data["num_chunks"] == 1
    assert data["processing_status"] == "completed"
    assert data["file_size"] == len(content)


@pytest.mark.asyncio
async def test_upload_rejects_bad_extension(client, auth_headers):
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("virus.exe", io.BytesIO(b"x"), "application/octet-stream")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
@patch("app.services.qa_service.generate_answer")
@patch("app.services.qa_service.search")
@patch("app.services.document_service.add_chunks")
async def test_ask_question(mock_add_chunks, mock_search, mock_generate, client, auth_headers):
    mock_add_chunks.return_value = 1
    mock_search.return_value = [{"text": "cats and dogs chunk", "filename": "notes2.txt", "document_id": 1}]
    mock_generate.return_value = "Cats and dogs are mentioned."

    content = b"This is a test document about cats and dogs."
    await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("notes2.txt", io.BytesIO(content), "text/plain")},
    )

    resp = await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "What animals are mentioned?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Cats and dogs" in data["answer"]
    assert "notes2.txt" in data["sources"]


@pytest.mark.asyncio
@patch("app.services.qa_service.search")
async def test_ask_without_documents(mock_search, client):
    mock_search.return_value = []
    await client.post("/api/v1/auth/register", json={"email": "nodoc@example.com", "password": "secret123"})
    resp = await client.post("/api/v1/auth/login", data={"username": "nodoc@example.com", "password": "secret123"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/api/v1/qa/ask", headers=headers, json={"question": "anything?"})
    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("app.services.document_service.add_chunks")
async def test_list_pagination_and_search(mock_add_chunks, client, auth_headers):
    mock_add_chunks.return_value = 1
    for name in ["alpha.txt", "beta.txt", "gamma.txt"]:
        await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": (name, io.BytesIO(b"some content"), "text/plain")},
        )

    resp = await client.get("/api/v1/documents/?page=1&limit=2", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 2

    resp = await client.get("/api/v1/documents/?search=beta", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert all("beta" in d["filename"] for d in body["items"])


@pytest.mark.asyncio
@patch("app.services.document_service.delete_user_document")
@patch("app.services.document_service.add_chunks")
async def test_rename_and_delete_document(mock_add_chunks, mock_delete_vec, client, auth_headers):
    mock_add_chunks.return_value = 1
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("rename_me.txt", io.BytesIO(b"content"), "text/plain")},
    )
    doc_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/documents/{doc_id}", headers=auth_headers, json={"filename": "renamed.txt"})
    assert resp.status_code == 200
    assert resp.json()["filename"] == "renamed.txt"

    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.patch(f"/api/v1/documents/{doc_id}", headers=auth_headers, json={"filename": "x.txt"})
    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("app.services.qa_service.generate_answer")
@patch("app.services.qa_service.search")
@patch("app.services.document_service.add_chunks")
async def test_dashboard_stats(mock_add_chunks, mock_search, mock_generate, client, auth_headers):
    mock_add_chunks.return_value = 1
    mock_search.return_value = [{"text": "chunk", "filename": "d.txt", "document_id": 1}]
    mock_generate.return_value = "answer"

    await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("d.txt", io.BytesIO(b"content"), "text/plain")},
    )
    await client.post("/api/v1/qa/ask", headers=auth_headers, json={"question": "what?"})

    resp = await client.get("/api/v1/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_documents"] >= 1
    assert data["questions_asked"] >= 1
