"""
POST /api/v1/ingest
Accepts a file upload, validates it, persists to disk, saves metadata to DB,
and fires off background processing via the ThreadPoolExecutor.
"""
import asyncio
import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.file_record import FileRecord, FileStatus
from app.schemas.file_schema import FileIngestResponse
from app.services.file_processor import process_file_async

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf"}


@router.post(
    "/ingest",
    response_model=FileIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and ingest a document",
)
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # ── 1. Validate extension ───────────────────────────────────────────
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # ── 2. Read content & validate size ────────────────────────────────
    content = await file.read()
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File size {file_size} bytes exceeds the 1 MB limit "
                f"({settings.MAX_FILE_SIZE_BYTES} bytes)."
            ),
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # ── 3. Duplicate detection via SHA-256 hash ─────────────────────────
    content_hash = hashlib.sha256(content).hexdigest()
    existing = await db.execute(
        select(FileRecord).where(FileRecord.content_hash == content_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A file with identical content has already been uploaded.",
        )

    # ── 4. Persist file to disk ─────────────────────────────────────────
    file_id = str(uuid.uuid4())
    upload_dir: Path = settings.UPLOAD_DIR / file_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest_path = upload_dir / file.filename

    async with aiofiles.open(dest_path, "wb") as out:
        await out.write(content)

    # ── 5. Save metadata to DB ──────────────────────────────────────────
    record = FileRecord(
        id=file_id,
        original_filename=file.filename,
        file_path=str(dest_path),
        file_size=file_size,
        content_hash=content_hash,
        mime_type=file.content_type,
        status=FileStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(record)
    await db.flush()   # write to DB before spawning worker

    # ── 6. Submit background processing task ───────────────────────────
    executor = request.app.state.executor
    client: AsyncOpenAI = request.app.state.openai_client
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        executor,
        lambda: asyncio.run(
            process_file_async(file_id, str(dest_path), file.filename, client)
        ),
    )

    logger.info("Accepted file '%s' with id=%s (%d bytes)", file.filename, file_id, file_size)

    return FileIngestResponse(
        file_id=file_id,
        original_filename=file.filename,
        file_size=file_size,
        status=FileStatus.PENDING,
        message="File accepted and queued for processing.",
        created_at=record.created_at,
    )
