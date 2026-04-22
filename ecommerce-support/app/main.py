"""
E-Commerce Multi-Agent Support  —  FastAPI Application
───────────────────────────────────────────────────────
The LangGraph workflow is compiled ONCE during application startup via the
FastAPI lifespan context manager and stored in app.state.workflow.
All incoming requests share the same compiled graph — no per-request
compilation overhead.

Run:
    uvicorn main:app --host 0.0.0.0 --port 9000 --reload

Environment variables (can also be set in .env):
    OPENAI_API_KEY               — required
    PRODUCT_MCP_BASE_URL         — default: http://localhost:8001/mcp
    REFUND_POLICY_MCP_BASE_URL   — default: http://localhost:8002/mcp
    ORDER_MCP_BASE_URL           — default: http://localhost:8003/mcp
    REFUND_MCP_BASE_URL          — default: http://localhost:8004/mcp
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Lifespan: compile workflow once at startup ───────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup  → compile the LangGraph workflow and store it on app.state.
    Shutdown → (nothing to clean up for an in-memory graph).
    """
    logger.info("Compiling LangGraph workflow …")
    from app.workflow import build_workflow
    app.state.workflow = build_workflow()
    logger.info("LangGraph workflow compiled and ready.")
    yield
    logger.info("Application shutdown.")


# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="E-Commerce Multi-Agent Support System",
    description=(
        "LangGraph + LangChain (OpenAI Model) powered customer support router.\n\n"
        "Router pattern: LLM classifier → specialist agent → synthesizer."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
)
def health():
    workflow_ready = hasattr(app.state, "workflow") and app.state.workflow is not None
    return {
        "status": "ok" if workflow_ready else "starting",
    }

@app.get("/settings", tags=["Health"], summary="Active configuration (non-sensitive)")
async def show_settings():
    """Inspect active config. OPENAI_API_KEY is intentionally omitted."""
    workflow_ready = hasattr(app.state, "workflow") and app.state.workflow is not None
    return {
        "workflow_compiled": workflow_ready,
        "model": settings.openai_model,
        "mcp_servers": {
            "product_mcp_url": settings.product_mcp_url,
            "refund_policy_mcp_url": settings.refund_policy_mcp_url,
            "order_mcp_url": settings.order_mcp_url,
            "refund_mcp_url": settings.refund_mcp_url,
        },
    }
