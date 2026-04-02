"""
app/tools/refund_tools.py

Tools layer — direct MongoDB query wrappers for the `refunds` collection.

Tool 1: lookup_return(return_id)
    → Fetches one document by `return_id` field.

Tool 2: get_return_by_order(order_id)
    → Fetches all return documents linked to a given `order_id`.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.db import get_database


# ---------------------------------------------------------------------------
# Tool 1 — single return by return_id
# ---------------------------------------------------------------------------

async def lookup_return(return_id: str) -> dict | None:
    """
    Fetch one document from the refunds collection by `return_id`.

    Returns the document as a plain dict (`_id` excluded via projection),
    or ``None`` when not found.
    """
    db: AsyncIOMotorDatabase = await get_database()

    doc = await db[settings.mongo_refunds_collection].find_one(
        {"return_id": return_id},
        {"_id": 0},
    )

    return doc


# ---------------------------------------------------------------------------
# Tool 2 — all returns for an order
# ---------------------------------------------------------------------------

async def get_return_by_order(order_id: str) -> list[dict]:
    """
    Fetch all return documents for a given `order_id`.

    Returns a list of dicts (`_id` excluded), sorted by `request_date`
    ascending (oldest request first).  Returns an empty list when no
    matching documents exist.
    """
    db: AsyncIOMotorDatabase = await get_database()

    cursor = db[settings.mongo_refunds_collection].find(
        {"order_id": order_id},
        {"_id": 0},
    ).sort("request_date", 1)

    return await cursor.to_list(length=None)
