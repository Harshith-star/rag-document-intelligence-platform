# RAG Document QA

A full-stack Retrieval-Augmented Generation app: upload documents, they're chunked and embedded into a FAISS index, and you ask questions answered by Gemini using the most relevant chunks as context.

Built with an interview-ready, layered backend: **Router → Service → Repository → PostgreSQL**, async SQLAlchemy 2.0, Alembic migrations, structured logging, and domain-specific exception handling.

## Architecture

![System architecture](docs/images/architecture.svg)

```
React (Axios, JWT)
   ↓
FastAPI Routers        ← thin controllers: parse request, call service, return response
   ↓
Services                ← business logic, orchestration, logging
   ↓
Repositories             ← all DB queries live here, nothing else touches the ORM directly
   ↓
PostgreSQL (async, via asyncpg) — schema versioned with Alembic
```

Vector search (FAISS) and document storage are separate concerns invoked from the service layer, so swapping Postgres for another RDBMS, or local disk for S3, doesn't touch business logic.

### AI processing pipeline

![AI pipeline](docs/images/ai_pipeline.svg)

`Upload → Extract Text (pypdf) → Chunk Text (800 chars / 100 overlap) → Embed (Gemini text-embedding-004) → Store in FAISS → on a question: check Redis cache → on a miss, embed query → retrieve top-k → Gemini generates a grounded answer → cache the answer`

### Caching AI responses (Redis)

Repeated questions are served from Redis instead of re-calling Gemini, using three complementary techniques:

1. **Versioned cache keys** (`qa_cache:user:{id}:v{cache_version}:{hash}`) — every `User` has a `cache_version` integer. The moment a document is uploaded, reprocessed, or deleted, `UserRepository.bump_cache_version()` atomically increments it. Every cache key built afterward embeds the new version, so old keys are instantly unreachable — there is no way for a stale answer to be looked up again, even by accident.
2. **Explicit delete-on-change** — on top of versioning, `DocumentService` calls `AnswerCache.invalidate_user()` after every upload/rename/delete, which scans and deletes the user's old-version keys from Redis immediately, instead of leaving them to expire on their own.
3. **TTL as a safety net** — every cache entry also carries a `CACHE_TTL_SECONDS` expiry (default 24h), so even in the (unlikely) case versioning or invalidation is skipped, Redis self-cleans rather than serving indefinitely-stale data.

Other details:
- Questions are normalized (trim + lowercase + collapse whitespace) before hashing, so `"What is deadlock?"` and `"  what   is deadlock?  "` hit the same entry.
- The cache **fails open**: if Redis is down or unreachable, `AnswerCache` logs a warning and falls back to a live Gemini call rather than breaking the endpoint — caching is a latency/cost optimization, not a hard dependency.
- The API response includes a `"cached": true/false` flag, surfaced in the UI as a ⚡ badge so you can see the cache working.

```python
# app/services/cache_service.py — versioned key construction
def build_cache_key(user_id: int, question: str, version: int) -> str:
    normalized = _normalize_question(question)
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"qa_cache:user:{user_id}:v{version}:{digest}"

class AnswerCache:
    async def get(self, key: str) -> dict | None:
        if not self.client:
            return None
        try:
            raw = await self.client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception:
            logger.warning("Cache read failed, falling back to live generation", exc_info=True)
            return None  # fail open

    async def invalidate_user(self, user_id: int) -> None:
        """Explicit delete-on-change: purge every cached answer for a user."""
        if not self.client:
            return
        async for key in self.client.scan_iter(match=f"qa_cache:user:{user_id}:*"):
            await self.client.delete(key)
```

```python
# app/services/document_service.py — invalidation triggered on every document change
async def _invalidate_cache_for_document_change(self, user_id: int) -> None:
    new_version = await self.user_repo.bump_cache_version(user_id)   # Option 3
    await self.cache.invalidate_user(user_id)                         # Option 1
    logger.info("Cache invalidated user_id=%s new_cache_version=%s", user_id, new_version)

# called from upload(), rename(), and delete()
```

```python
# app/services/qa_service.py — usage in the QA flow
current_user = await self.user_repo.get_by_id(user.id)  # fresh version, not the stale JWT-loaded user
cache_key = build_cache_key(user.id, question, current_user.cache_version)

cached = await self.cache.get(cache_key)
if cached is not None:
    return {**cached, "cached": True}

# ... cache miss: retrieve from FAISS, call Gemini ...
response = {"answer": answer, "sources": sources}
await self.cache.set(cache_key, response)  # TTL applied here
return {**response, "cached": False}
```

**Interview framing** — *"Won't Redis return outdated answers if a document changes?"* It would, if cache entries weren't invalidated. To prevent that, every document upload/edit/delete bumps a per-user `cache_version`, which is embedded in the cache key (`user_id:version:hash`), so updated content automatically gets a fresh cache namespace. On top of that, the old keys are explicitly deleted rather than left to expire, and every entry still carries a TTL as a last line of defense. The combination means stale answers can't be served, and Redis doesn't accumulate dead keys waiting on a timer.

### Database schema

![Database schema](docs/images/db_schema.svg)

Each user owns many `documents` and many `query_logs` (1:N). FAISS indexes live outside Postgres on disk, one flat index per user, keyed by `document_id` in a JSON metadata sidecar — this keeps vector search fast without needing a vector-capable database. `users.cache_version` (added in a later migration) is an integer bumped on every document change and embedded directly in Redis cache keys for AI answers — see "Caching AI responses" below.

### Request sequence: asking a question

![QA sequence diagram](docs/images/sequence_qa.svg)

## Project layout

```
ragapp/
  backend/
    app/
      main.py                  FastAPI app, CORS, global exception handler, logging setup
      config.py                  env-driven settings (DB URL, Gemini keys, upload limits)
      database.py                  async SQLAlchemy engine/session
      models.py                     User, Document, QueryLog ORM models
      schemas.py                     Pydantic request/response models
      auth.py                          JWT issuing/verification, password hashing
      exceptions.py                     domain-specific exceptions (AppError subclasses)
      logging_config.py                  structured logging setup
      routers/                            thin controllers only
        auth.py                             register / login / me / update profile
        documents.py                          upload, list (paginated+search), rename, delete
        qa.py                                   ask question
        dashboard.py                             aggregated usage stats
      services/                             business logic layer
        auth_service.py
        document_service.py
        qa_service.py
        document_processor.py                   PDF/text extraction + chunking
        vector_store.py                          FAISS index read/write/search/delete
        gemini_service.py                        Gemini embeddings + chat completion
      repositories/                         DB access layer (no business logic)
        user_repository.py
        document_repository.py
        query_log_repository.py
    alembic/                  versioned schema migrations
    tests/                      pytest suite (async, Gemini calls mocked)
    Dockerfile
    requirements.txt
  frontend/
    src/
      api.js                  axios client w/ JWT interceptor
      AuthContext.jsx          auth state provider
      App.jsx                   router
      pages/                      Login, Register, Dashboard (stats, upload, search, chat)
      components/ProtectedRoute.jsx
    Dockerfile               builds with Vite, serves via nginx
    nginx.conf                proxies /auth, /documents, /qa, /dashboard to backend
  docs/images/             architecture diagrams used in this README
  docker-compose.yml      postgres + backend + frontend
  .env.example
```

## Running with Docker (recommended)

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY, SECRET_KEY, POSTGRES_PASSWORD
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8000/docs`
- Postgres: `localhost:5432` (user `raguser`, db `ragdb`)
- Redis: `localhost:6379` (used to cache repeated AI answers)

The backend container runs `alembic upgrade head` before starting uvicorn, so the schema is always up to date on boot. Vector indexes and uploaded files persist in the `backend_storage` volume; database data persists in `postgres_data`.

## Running locally (without Docker)

**Backend** — requires a running PostgreSQL instance and a Redis instance (for answer caching; the app still works with `CACHE_ENABLED=false` if you skip Redis):
```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://raguser:ragpass@localhost:5432/ragdb
export REDIS_URL=redis://localhost:6379/0
export GEMINI_API_KEY=your-key-here
export SECRET_KEY=some-random-string
alembic upgrade head
uvicorn app.main:app --reload
```
API docs at `http://localhost:8000/docs`.

**Frontend**
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` (Vite dev server proxies `/auth`, `/documents`, `/qa`, `/dashboard` to `localhost:8000`).

## Database migrations (Alembic)

```bash
cd backend
# create a new migration after changing models.py
alembic revision --autogenerate -m "describe the change"
# apply migrations
alembic upgrade head
# roll back one revision
alembic downgrade -1
```
Schema is never created with `Base.metadata.create_all()` in this project — every change is a versioned, reviewable migration in `backend/alembic/versions/` (currently two: initial schema, then adding `users.cache_version` for the Redis cache).

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```
Tests run against an in-memory async SQLite database (via `aiosqlite`) so no Postgres instance is required locally, and all Gemini API calls are mocked.

## API summary

| Method | Path                  | Auth | Description                                          |
|--------|-----------------------|------|-------------------------------------------------------|
| POST   | `/auth/register`      | no   | Create account                                        |
| POST   | `/auth/login`         | no   | OAuth2 password flow, returns JWT                     |
| GET    | `/auth/me`            | yes  | Current user profile                                  |
| PUT    | `/auth/me`            | yes  | Update profile (full name)                            |
| POST   | `/documents/upload`   | yes  | Upload + process a .pdf/.txt/.md file                 |
| GET    | `/documents/`         | yes  | List documents — paginated (`page`, `limit`), `search` by filename |
| PATCH  | `/documents/{id}`     | yes  | Rename a document                                     |
| DELETE | `/documents/{id}`     | yes  | Delete a document and its vectors                     |
| POST   | `/qa/ask`             | yes  | Ask a question over uploaded docs — checks Redis cache first; response includes `cached: bool` |
| GET    | `/dashboard/stats`    | yes  | Total docs, storage used, questions asked, avg response time |

All error responses follow a consistent shape (`{"detail": "..."}`) via a global exception handler mapping domain exceptions (`UserAlreadyExistsError`, `DocumentNotFoundError`, `NoDocumentsError`, etc.) to the correct HTTP status code.

## Configuration (env vars)

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | dev-secret-change-me | JWT signing secret — set a strong value in production |
| `DATABASE_URL` | `postgresql+asyncpg://raguser:ragpass@localhost:5432/ragdb` | Async SQLAlchemy connection string |
| `GEMINI_API_KEY` | (empty) | Required for embeddings + answer generation |
| `GEMINI_MODEL` | gemini-1.5-flash | Chat model used for answers |
| `EMBEDDING_MODEL` | models/text-embedding-004 | Embedding model |
| `LOG_LEVEL` | INFO | Python logging level |
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection string for AI answer caching |
| `CACHE_ENABLED` | true | Disable to bypass Redis entirely (always call Gemini) |
| `CACHE_TTL_SECONDS` | 86400 | How long a cached answer stays valid |

## Design notes / what this demonstrates

- **Layered architecture** — routers never touch the ORM or contain business rules; services own logic and logging; repositories own queries. Easy to unit-test each layer in isolation and easy to explain in a system-design interview.
- **Async all the way down** — SQLAlchemy 2.0 async engine + asyncpg, matching FastAPI's async request lifecycle instead of blocking the event loop with sync DB calls.
- **Schema as code** — Alembic migrations are reviewable, versioned, and reversible; no implicit `create_all()` in production code paths.
- **Specific exceptions, not broad catches** — each failure mode (duplicate user, missing document, unsupported file type, no documents to search, generation failure) is its own exception type mapped to the right HTTP status by one global handler, so routers stay free of `try/except`.
- **Structured logging** — key lifecycle events (upload started/completed, login, QA request processed) are logged with structured fields (`user_id`, `document_id`, timings) instead of print statements.
- **Observability-friendly data model** — `processing_status`, `processing_time`, and `query_logs` make the dashboard's metrics (documents, storage used, questions asked, average response time) real aggregate queries, not placeholders.
- **Cache invalidation done right** — repeated questions skip Gemini via Redis, but every document change (upload/rename/delete) bumps a per-user `cache_version` *and* explicitly purges old keys, with a TTL as a final safety net — three layers so stale answers can't leak through, and the cache fails open if Redis is unavailable.

## Future improvements

- Swap local disk storage for an object store (S3 / GCS) behind the same `DocumentService` interface — no router or service signature changes needed, only the storage adapter.
- Replace FAISS `IndexFlatL2` with an IVF/HNSW index once a single user's corpus grows large enough that linear scan becomes a bottleneck.
- Add rate limiting and per-user quota enforcement in front of `/documents/upload`.
- Add Prometheus metrics / OpenTelemetry tracing around the service layer for production observability.
- Add refresh tokens and token revocation instead of long-lived single access tokens.
