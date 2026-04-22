"""
Centralised application settings.

Loads environment variables from `.env` once using Pydantic BaseSettings and
exposes a singleton `settings` object for the rest of the codebase.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment/.env."""

    # OpenAI
    openai_api_key: str
    openai_model: str

    # MCP Server URLs
    product_mcp_base_url: str
    refund_policy_mcp_base_url: str
    order_mcp_base_url: str
    refund_mcp_base_url: str

    @property
    def product_mcp_url(self) -> str:
        return f"{self.product_mcp_base_url}/mcp"

    @property
    def refund_policy_mcp_url(self) -> str:
        return f"{self.refund_policy_mcp_base_url}/mcp"

    @property
    def order_mcp_url(self) -> str:
        return f"{self.order_mcp_base_url}/mcp"

    @property
    def refund_mcp_url(self) -> str:
        return f"{self.refund_mcp_base_url}/mcp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so we only read `.env` once."""

    return Settings()


# Singleton exported for convenience
settings = get_settings()
