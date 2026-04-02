from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.file_record import FileStatus


# ──────────────────────────────────────────────
# File schemas
# ──────────────────────────────────────────────

class FileIngestResponse(BaseModel):
    file_id: str
    original_filename: str
    file_size: int
    status: FileStatus
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FileStatusResponse(BaseModel):
    file_id: str
    original_filename: str
    file_size: int
    mime_type: Optional[str]
    status: FileStatus
    chunk_count: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FileListResponse(BaseModel):
    total: int
    files: List[FileStatusResponse]


# ──────────────────────────────────────────────
# RAG / Retrieval schemas
# ──────────────────────────────────────────────

class RetrievedChunk(BaseModel):
    file_id: str
    original_filename: str
    chunk_index: int
    text: str
    score: float


class RetrievalResponse(BaseModel):
    query: str
    results: List[RetrievedChunk]
