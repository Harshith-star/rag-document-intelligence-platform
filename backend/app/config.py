"""Application configuration — all values loaded from environment variables.

SECRET_KEY and DATABASE_URL are required; the app refuses to start without them
so insecure defaults can never silently reach production.
"""

import sys
from pathlib import Path


from dotenv import load_dotenv
import os
load_dotenv()
def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"[FATAL] Environment variable '{name}' is required but not set.", file=sys.stderr)
        sys.exit(1)
    return val


# ── paths ─────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent.parent
STORAGE_DIR   = BASE_DIR / "storage"
UPLOAD_DIR    = STORAGE_DIR / "uploads"
VECTOR_DIR    = STORAGE_DIR / "vectors"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

# ── required ──────────────────────────────────────────────────────────────
SECRET_KEY   = _require("SECRET_KEY")      # aborts startup if missing
DATABASE_URL = _require("DATABASE_URL")    # aborts startup if missing

# ── optional with sensible defaults ──────────────────────────────────────
ALGORITHM                 = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL",    "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

CHUNK_SIZE           = int(os.getenv("CHUNK_SIZE",    "800"))
CHUNK_OVERLAP        = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K                = int(os.getenv("TOP_K",         "4"))
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(20 * 1024 * 1024)))
ALLOWED_EXTENSIONS   = {".pdf", ".txt", ".md"}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

REDIS_URL         = os.getenv("REDIS_URL",         "redis://localhost:6379/0")
CACHE_ENABLED     = os.getenv("CACHE_ENABLED",     "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", str(60 * 60 * 24)))

# ── startup timestamp (used by /health uptime) ────────────────────────────
import time as _time
APP_START_TIME: float = _time.time()
