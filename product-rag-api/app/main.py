"""
Main FastAPI application entry point.

Lifespan:
  - Creates the ThreadPoolExecutor and stores it in app.state.executor
  - Loads the embedding model into the global vector_store singleton
  - Initialises PostgreSQL tables + pgvector extension via SQLAlchemy
  - Creates the HNSW / IVFFlat index on the embedding column
  - Tears everything down cleanly on shutdown
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.db.session import init_db
from app.services.vector_store import vector_store

from openai import AsyncOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan (replaces deprecated on_event startup/shutdown)
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Everything before `yield` runs at startup;
    everything after `yield` runs at shutdown.
    """
    logger.info("═══ Application startup ═══")

    # 1. Ensure uploads directory exists
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory ready: %s", settings.UPLOAD_DIR)

    # 2. Initialise PostgreSQL: enable pgvector extension + create ORM tables
    await init_db()
    logger.info("PostgreSQL tables initialised.")

    # 3. Create the HNSW / IVFFlat vector index (idempotent)
    await vector_store.create_index()

    # 4. Create the shared ThreadPoolExecutor and attach to app state
    executor = ThreadPoolExecutor(
        max_workers=settings.MAX_WORKERS,
        thread_name_prefix="rag-worker",
    )
    app.state.executor = executor
    logger.info("ThreadPoolExecutor created (max_workers=%d).", settings.MAX_WORKERS)

    # 5. Initialize the OpenAI client once for the entire application life
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    app.state.openai_client = client

    logger.info("═══ Startup complete – application is ready ═══")

    yield  # ← application runs here

    # ── Shutdown ────────────────────────────────────────────────────────
    logger.info("═══ Application shutdown ═══")
    executor.shutdown(wait=True, cancel_futures=False)
    logger.info("ThreadPoolExecutor shut down.")

    # Ensure the client connection is closed gracefully
    await client.close()
# ──────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Product RAG ingestion pipeline: upload documents, track processing status, "
        "and retrieve semantically relevant chunks."
    ),
    lifespan=lifespan,
)

# CORS (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes under /api/v1
app.include_router(api_router, prefix="/product-rag/api/v1")


# ──────────────────────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}

@app.get("/settings", tags=["Health"], summary="Active configuration (non-sensitive)")
async def show_settings():
    """Inspect active config. OPENAI_API_KEY is intentionally omitted."""
    return {
        "postgres_host": settings.POSTGRES_HOST,
        "postgres_port": settings.POSTGRES_PORT,
        "postgres_db": settings.POSTGRES_DB,
        "postgres_user": settings.POSTGRES_USER,
        "postgres_password": settings.POSTGRES_PASSWORD,
    }