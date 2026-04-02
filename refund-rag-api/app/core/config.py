from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Refund RAG Ingestion API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # File storage
    UPLOAD_DIR: Path = Path("uploads")
    MAX_FILE_SIZE_BYTES: int = 1 * 1024 * 1024  # 1 MB

    # ── PostgreSQL (metadata + pgvector) ──────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ragdb"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    @property
    def DATABASE_URL(self) -> str:
        """Async SQLAlchemy URL for asyncpg driver."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync psycopg2 URL (used only for Alembic / raw psycopg2 bootstrap)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Thread pool
    MAX_WORKERS: int = 4

    # Chunking
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # Embedding model
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1024

    # Retrieval
    TOP_K_RESULTS: int = 5

    # pgvector index type: "hnsw" or "ivfflat"
    PGVECTOR_INDEX_TYPE: str = "hnsw"

    OPENAI_API_KEY: str = "YOUR_OPENAI_API_KEY_HERE"

    class Config:
        env_file = ".env"


settings = Settings()

