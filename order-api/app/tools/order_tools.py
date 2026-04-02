"""
app/tools/order_tools.py

Tools layer — direct MongoDB query wrappers.

The `orders` collection stores the full order document including the
`tracking_updates` array embedded inside it.  There is NO separate
tracking_history collection — both tools query the same `orders` collection.

Tool 1: lookup_order(order_id)
    → Returns the full order document (minus tracking_updates).

Tool 2: get_tracking_updates(order_id)
    → Returns the embedded tracking_updates array for an order.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.db import get_database


# ---------------------------------------------------------------------------
# Tool 1 — full order document
# ---------------------------------------------------------------------------

async def lookup_order(order_id: str) -> dict | None:
    """
    Fetch one document from the orders collection by `order_id` field.

    Returns the document as a plain dict with `_id` removed (the
    application uses `order_id` as the canonical identifier), or
    ``None`` when not found.
    """
    db: AsyncIOMotorDatabase = await get_database()

    doc = await db[settings.mongo_orders_collection].find_one(
        {"order_id": order_id},
        {"_id": 0},   # exclude Mongo internal _id from results
    )

    return doc   # None if not found


# ---------------------------------------------------------------------------
# Tool 2 — embedded tracking updates
# ---------------------------------------------------------------------------

async def get_tracking_updates(order_id: str) -> list[dict]:
    """
    Fetch the `tracking_updates` array embedded in the order document.

    Returns the list of tracking-event dicts, or an empty list when the
    order does not exist or has no events yet.
    """
    db: AsyncIOMotorDatabase = await get_database()

    doc = await db[settings.mongo_orders_collection].find_one(
        {"order_id": order_id},
        {"_id": 0, "tracking_updates": 1},   # project only what we need
    )

    if doc is None:
        return []

    return doc.get("tracking_updates", [])
