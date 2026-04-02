"""
PgVectorStore – stores and retrieves document chunk embeddings using
PostgreSQL + pgvector.

All write operations are async (called from background worker via asyncio.run),
and all read operations are async (called directly from FastAPI route handlers).
"""
import logging
from typing import List, Tuple

from sqlalchemy import delete, select, text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.document_chunk import DocumentChunk

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class PgVectorStore:
    """
    Thin async wrapper around the document_chunks table.
    Embedding generation lives here
    """

    # ──────────────────────────────────────────────────────────────────
    # Index creation (called once after init_db)
    # ──────────────────────────────────────────────────────────────────

    async def create_index(self) -> None:
        """
        Create an HNSW (or IVFFlat) index on the embedding column if it
        doesn't already exist.  HNSW is preferred: no need to set lists.
        """
        index_type = settings.PGVECTOR_INDEX_TYPE.lower()
        index_name = "ix_document_chunks_embedding"

        if index_type == "hnsw":
            ddl = f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON document_chunks
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """
        else:  # ivfflat
            ddl = f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON document_chunks
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """

        async with AsyncSessionLocal() as session:
            await session.execute(text(ddl))
            await session.commit()
        logger.info("pgvector index '%s' (%s) ensured.", index_name, index_type)

    # ──────────────────────────────────────────────────────────────────
    # Write (async – called from background worker via asyncio.run)
    # ──────────────────────────────────────────────────────────────────

    async def add_chunks(
        self, file_id: str, filename: str, chunks: List[str], client: AsyncOpenAI, async_session
    ) -> None:
        """Embed all chunks and bulk-insert into document_chunks."""
        if not chunks:
            return

        embeddings = await self._get_async_embeddings(chunks, client)

        rows = [
            DocumentChunk(
                file_id=file_id,
                original_filename=filename,
                chunk_index=idx,
                text=chunk_text,
                embedding=embedding,
            )
            for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings))
        ]

        async with async_session() as session:
            session.add_all(rows)
            await session.commit()

        logger.info(
            "Inserted %d chunks for file_id=%s into pgvector.", len(rows), file_id
        )

    # ──────────────────────────────────────────────────────────────────
    # Read (async – called from FastAPI route)
    # ──────────────────────────────────────────────────────────────────

    async def search(
        self, client: AsyncOpenAI, query: str, top_k: int = 5, 
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Return the top_k most similar chunks using cosine distance (<=>).
        1 - cosine_distance == cosine_similarity → score in [0, 1].
        """
        embeddings = await self._get_async_embeddings([query], client)
        q_vec = embeddings[0]

        # pgvector cosine distance operator: <=>
        stmt = (
            select(
                DocumentChunk,
                (1 - DocumentChunk.embedding.cosine_distance(q_vec)).label("score"),
            )
            .order_by(DocumentChunk.embedding.cosine_distance(q_vec))
            .limit(top_k)
        )

        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt)
            rows = result.all()

        return [(chunk, float(score)) for chunk, score in rows]

    # ──────────────────────────────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────────────────────────────

    async def remove_file(self, file_id: str) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.file_id == file_id)
            )
            await session.commit()
        logger.info("Deleted all chunks for file_id=%s.", file_id)

    # ──────────────────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────────────────

    async def _get_async_embeddings(self, texts: List[str], client: AsyncOpenAI):
        response = await client.embeddings.create(
            input=texts,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSION
        )
        # Extract all the embedding vectors from the response data
        embeddings = [data.embedding for data in response.data]
        return embeddings

# ── Module-level singleton ─────────────────────────────────────────────────
vector_store = PgVectorStore()
