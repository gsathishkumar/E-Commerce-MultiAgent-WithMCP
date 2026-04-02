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
    
    # Tool endpoints base url
    product_rag_base_url: str
    refund_policy_rag_base_url: str
    order_api_base_url: str
    refund_api_base_url: str

    # Tool endpoints url (computed so env overrides to base URLs flow through)
    @property
    def product_rag_url(self) -> str:
        return f"{self.product_rag_base_url}/product-rag/api/v1/retrieve"

    @property
    def refund_policy_rag_url(self) -> str:
        return f"{self.refund_policy_rag_base_url}/refund-rag/api/v1/retrieve"

    @property
    def order_api_url(self) -> str:
        return f"{self.order_api_base_url}/order-api/api/v1/orders"

    @property
    def refund_api_url(self) -> str:
        return f"{self.refund_api_base_url}/refund-api/api/v1/refunds"

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
