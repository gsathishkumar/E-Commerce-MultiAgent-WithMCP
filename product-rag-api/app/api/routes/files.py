"""
GET /api/v1/files          – list all files with their statuses
GET /api/v1/files/status   – get a single file status by ?file_id=
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.file_record import FileRecord
from app.schemas.file_schema import FileListResponse, FileStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(record: FileRecord) -> FileStatusResponse:
    return FileStatusResponse(
        file_id=record.id,
        original_filename=record.original_filename,
        file_size=record.file_size,
        mime_type=record.mime_type,
        status=record.status,
        chunk_count=record.chunk_count,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get(
    "/files",
    response_model=FileListResponse,
    summary="List all uploaded files with their processing status",
)
async def list_files(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FileRecord).order_by(FileRecord.created_at.desc()))
    records = result.scalars().all()
    return FileListResponse(
        total=len(records),
        files=[_to_response(r) for r in records],
    )


@router.get(
    "/files/status",
    response_model=FileStatusResponse,
    summary="Get processing status of a specific file",
)
async def get_file_status(
    file_id: str = Query(..., description="The file ID returned at upload time"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FileRecord).where(FileRecord.id == file_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No file found with id='{file_id}'.",
        )
    return _to_response(record)
