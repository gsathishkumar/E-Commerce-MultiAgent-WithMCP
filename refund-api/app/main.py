"""
app/main.py — FastAPI application entry point.

Run:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from app.config import settings
from app.db import close_db, connect_db
from app.routes.refund_routes import router as refund_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title=settings.app_name,
    description=(
        "FastAPI service exposing return request details and per-order return"
        "history from MongoDB.\n\n"
        "**Layers:** Routes → Services → Tools → MongoDB `refunds` collection"
    ),
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(refund_router, prefix=settings.api_v1_prefix)

mcp = FastApiMCP(app, 
                 name="RefundDB as MCP Server",
                 description="MCP service exposing return request details and per-order return",
                 describe_all_responses=True,
                 describe_full_response_schema=True,
                 include_operations=["get_return_details","get_all_returns_by_order"])
mcp.mount_http()
# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"], summary="Liveness probe")
async def health():
    return {"status": "ok", "env": settings.app_environment, "version": settings.app_version}


@app.get("/settings", tags=["Health"], summary="Active configuration (non-sensitive)")
async def show_settings():
    """Inspect active config. MONGO_URI is intentionally omitted."""
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "app_environment": settings.app_environment,
        "debug": settings.debug,
        "api_v1_prefix": settings.api_v1_prefix,
        "mongo_uri": settings.mongo_uri,
        "mongo_db": settings.mongo_db_name,
        "mongo_refunds_collection": settings.mongo_refunds_collection,
        "mongo_connect_timeout_ms": settings.mongo_connect_timeout_ms,
        "mongo_server_selection_timeout_ms": settings.mongo_server_selection_timeout_ms,
    }