"""FastAPI application entry point.

Startup order:
  1. configure_logging()
  2. App + middleware wired
  3. Global AppError → JSON handler
  4. All routers mounted under /api/v1
  5. /health  — liveness  (always returns 200 once the process is up)
  6. /ready   — readiness (checks Postgres + Redis; returns 503 if either is down)
"""
import time

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import APP_START_TIME, REDIS_URL
from .database import engine
from .exceptions import AppError
from .logging_config import configure_logging, get_logger
from .routers import auth, dashboard, documents, qa

configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="DocuMind RAG API",
    version="2.1.0",
    description=(
        "Production-grade RAG platform — semantic document search, "
        "grounded Q&A with citations, Redis answer caching, "
        "Alembic-managed PostgreSQL schema."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "AppError path=%s status=%s detail=%s",
        request.url.path, exc.status_code, exc.detail,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ── versioned API routers ─────────────────────────────────────────────────
_PREFIX = "/api/v1"
app.include_router(auth.router,      prefix=_PREFIX)
app.include_router(documents.router, prefix=_PREFIX)
app.include_router(qa.router,        prefix=_PREFIX)
app.include_router(dashboard.router, prefix=_PREFIX)


# ── liveness probe ────────────────────────────────────────────────────────
@app.get("/health", tags=["ops"], summary="Liveness — is the process alive?")
async def health():
    """Returns 200 as soon as the process is up.
    Docker / k8s liveness probes should call this endpoint."""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - APP_START_TIME, 1),
        "version": "2.1.0",
    }


# ── readiness probe ───────────────────────────────────────────────────────
@app.get("/ready", tags=["ops"], summary="Readiness — are all dependencies up?")
async def ready():
    """Returns 200 only when both PostgreSQL and Redis are reachable.
    Docker / k8s readiness probes should call this endpoint.
    Load balancers should stop sending traffic when this returns 503."""
    checks: dict[str, str] = {}
    ok = True

    # Postgres check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
        ok = False

    # Redis check
    try:
        r = aioredis.from_url(REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        ok = False

    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if ok else "not_ready", "checks": checks},
    )
