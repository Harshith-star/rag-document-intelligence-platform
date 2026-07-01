"""Test fixtures.

Uses sqlite+aiosqlite for the DB and fakeredis for the cache so no real
Postgres or Redis server is needed.
"""
import os, sys, tempfile
import pytest, pytest_asyncio

_db = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db}"
os.environ["SECRET_KEY"]   = "test-secret-key-not-for-production"
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ["CACHE_ENABLED"] = "true"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fakeredis.aioredis
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database import Base, engine
import app.services.cache_service as cache_svc


# Create a fresh FakeRedis bound to the current event loop for each test.
# A session-scoped singleton would be bound to a different loop and raise
# "bound to a different event loop" RuntimeError.
@pytest.fixture(autouse=True)
def _fresh_fake_redis():
    cache_svc._redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield
    cache_svc._redis_client = None


@pytest_asyncio.fixture(autouse=True, scope="session")
async def _create_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "secret123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "secret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
