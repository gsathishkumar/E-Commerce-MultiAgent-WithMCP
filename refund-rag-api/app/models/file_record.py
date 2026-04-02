import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    Enum as SAEnum, Text
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class FileStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, index=True)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)       # bytes
    content_hash = Column(String, nullable=False, unique=True, index=True)
    mime_type = Column(String, nullable=True)
    status = Column(SAEnum(FileStatus), default=FileStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
