"""
app/db.py — MongoDB async connection (Motor).

All parameters come from app.config.settings.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    """Open the Motor client. Called once at app startup via lifespan."""
    global _client
    _client = AsyncIOMotorClient(
        settings.mongo_uri,
        connectTimeoutMS=settings.mongo_connect_timeout_ms,
        serverSelectionTimeoutMS=settings.mongo_server_selection_timeout_ms,
    )
    await _client.admin.command("ping")   # fail fast on bad URI / network


async def close_db() -> None:
    """Close the Motor client. Called once at app shutdown via lifespan."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def get_database() -> AsyncIOMotorDatabase:
    """Return the active database handle (lazy-opens if needed)."""
    global _client
    if _client is None:
        await connect_db()
    return _client[settings.mongo_db_name]
