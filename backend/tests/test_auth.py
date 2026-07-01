import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    resp = await client.post("/api/v1/auth/register", json={"email": "alice@example.com", "password": "pw123456"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"

    resp = await client.post("/api/v1/auth/login", data={"username": "alice@example.com", "password": "pw123456"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_duplicate_registration_fails(client):
    await client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "pw123456"})
    resp = await client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "pw123456"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={"email": "bob@example.com", "password": "pw123456"})
    resp = await client.post("/api/v1/auth/login", data={"username": "bob@example.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_update_profile(client, auth_headers):
    resp = await client.put("/api/v1/auth/me", headers=auth_headers, json={"full_name": "Test User"})
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Test User"
