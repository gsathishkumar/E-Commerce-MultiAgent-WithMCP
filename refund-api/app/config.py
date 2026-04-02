"""
app/config.py — centralised project settings via Pydantic Settings.

All values are read from environment variables or a .env file.
Import the singleton anywhere in the project:

    from app.config import settings
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Project-wide settings.

    Precedence (highest → lowest):
      1. Actual environment variables
      2. .env file
      3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_name: str = Field(default="Refunds API", description="OpenAPI service title.")
    app_version: str = Field(default="1.0.0", description="Semantic version string.")
    app_environment: str = Field(
        default="development",
        description="Runtime environment: development | staging | production.",
    )
    debug: bool = Field(default=False, description="Enable FastAPI debug mode.")

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    api_v1_prefix: str = Field(default="/refund-api/api/v1", description="URL prefix for v1 routes.")

    # ------------------------------------------------------------------
    # MongoDB
    # ------------------------------------------------------------------
    mongo_db_host: str = "localhost"
    mongo_db_port: int = 27017
    mongo_db_user: str = "admin"
    mongo_db_password: str = "SecurePassword123"

    @property
    def mongo_uri(self) -> str:
        """Mongo URL."""

        return (
            f"mongodb://{self.mongo_db_user}:{self.mongo_db_password}"
            f"@{self.mongo_db_host}:{self.mongo_db_port}/?authSource={self.mongo_db_name}"
        )
    
    mongo_db_name: str = Field(default="refunds_db", description="MongoDB database name.")
    mongo_refunds_collection: str = Field(
        default="refunds",
        description="Collection storing return/refund documents.",
    )
    mongo_connect_timeout_ms: int = Field(
        default=5_000, description="Connection timeout in milliseconds."
    )
    mongo_server_selection_timeout_ms: int = Field(
        default=5_000, description="Server-selection timeout in milliseconds."
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("app_environment")
    @classmethod
    def validate_app_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v.lower() not in allowed:
            raise ValueError(f"app_environment must be one of {allowed}, got '{v}'.")
        return v.lower()

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton (reads .env once)."""
    return Settings()


# Convenience singleton — preferred import target
settings: Settings = get_settings()

dict_from_dict_attr = settings.__dict__
print(f"Loaded Settings: {dict_from_dict_attr}")
