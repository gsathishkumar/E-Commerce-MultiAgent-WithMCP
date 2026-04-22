"""
GET /api/v1/retrieve?query=<text>&top_k=<int>
Returns relevant chunks from the vector store for the given query.
"""
import logging

from fastapi import APIRouter, HTTPException, Request, Query, status

from app.core.config import settings
from app.schemas.file_schema import RetrievalResponse, RetrievedChunk
from app.services.vector_store import vector_store

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/retrieve",
    response_model=RetrievalResponse,
    summary="Retrieve relevant document chunks for a natural-language query",
    operation_id="get_product_chunks_by_query"
)
async def retrieve(
    request: Request,
    query: str = Query(..., min_length=1, description="Natural-language search query"),
    top_k: int = Query(
        default=None,
        ge=1,
        le=20,
        description="Number of top chunks to return (default from settings)",
    ),
):
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must not be empty.",
        )
    client: AsyncOpenAI = request.app.state.openai_client
    k = top_k or settings.TOP_K_RESULTS
    hits = await vector_store.search(client, query, top_k=k)

    if not hits:
        return RetrievalResponse(query=query, results=[])

    results = [
        RetrievedChunk(
            file_id=meta.file_id,
            original_filename=meta.original_filename,
            chunk_index=meta.chunk_index,
            text=meta.text,
            score=score,
        )
        for meta, score in hits
    ]

    logger.info("Retrieval for query=%r → %d results", query[:60], len(results))
    return RetrievalResponse(query=query, results=results)
