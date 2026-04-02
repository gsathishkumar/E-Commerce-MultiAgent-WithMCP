"""
Background worker that runs in the ThreadPoolExecutor.
It processes an uploaded file: parses text → chunks → embeds → stores in pgvector.
"""
import logging
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.file_record import FileRecord, FileStatus
from app.services.file_parser import extract_text
from app.services.vector_store import vector_store

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def process_file_async(file_id: str, file_path: str, original_filename: str, client: AsyncOpenAI) -> None:
    """
    Async coroutine called from the ThreadPoolExecutor via asyncio.run().
    Pipeline: PENDING → PROCESSING → (chunk + embed + pgvector insert) → COMPLETED | FAILED
    """
    logger.info("Starting processing for file_id=%s", file_id)
    try:
        # ✅ Create engine INSIDE this Event loop
        engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

        async_session = async_sessionmaker(
            engine, class_= AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
        )

        # ── Mark as PROCESSING ──────────────────────────────────────────────
        async with async_session() as session:
            await session.execute(
                update(FileRecord)
                .where(FileRecord.id == file_id)
                .values(status=FileStatus.PROCESSING, updated_at=datetime.utcnow())
            )
            await session.commit()

        # ── Extract text ─────────────────────────────────────────────────
        raw_text = extract_text(file_path)
        if not raw_text.strip():
            raise ValueError("No extractable text found in the file.")

        # ── Chunk the text ────────────────────────────────────────────────
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        chunks = splitter.split_text(raw_text)
        logger.info("file_id=%s → %d chunks produced.", file_id, len(chunks))

        # ── Embed and store in pgvector (async) ───────────────────────────
        await vector_store.add_chunks(file_id, original_filename, chunks, client, async_session)

        # ── Mark COMPLETED ────────────────────────────────────────────────
        async with async_session() as session:
            await session.execute(
                update(FileRecord)
                .where(FileRecord.id == file_id)
                .values(
                    status=FileStatus.COMPLETED,
                    chunk_count=len(chunks),
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()

        logger.info("file_id=%s processing COMPLETED (%d chunks).", file_id, len(chunks))

    except Exception as exc:
        logger.exception("Processing failed for file_id=%s", file_id)
        async with async_session() as session:
            await session.execute(
                update(FileRecord)
                .where(FileRecord.id == file_id)
                .values(
                    status=FileStatus.FAILED,
                    error_message=str(exc),
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()
    finally:
        await engine.dispose() 

