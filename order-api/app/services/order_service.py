"""
app/services/order_service.py

Service layer — business logic between the API routes and the tools.
"""

from fastapi import HTTPException, status

from app.schemas.order_schemas import OrderResponse, TrackingResponse, TrackingEvent
from app.tools.order_tools import get_tracking_updates, lookup_order


async def get_order_details(order_id: str) -> OrderResponse:
    """
    Fetch and validate a full order document.

    Raises:
        HTTPException 404 — when no order matches `order_id`.
    """
    doc = await lookup_order(order_id)

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found.",
        )

    # Strip the embedded array — the detail endpoint does not expose it
    doc.pop("tracking_updates", None)

    return OrderResponse(**doc)


async def get_order_tracking(order_id: str) -> TrackingResponse:
    """
    Fetch the tracking history for an order.

    Validates the order exists (404 if not), then returns shipment
    metadata plus the full `tracking_updates` array.

    Raises:
        HTTPException 404 — when no order matches `order_id`.
    """
    doc = await lookup_order(order_id)

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found.",
        )

    updates = await get_tracking_updates(order_id)

    return TrackingResponse(
        order_id=doc["order_id"],
        tracking_id=doc.get("tracking_id", None),
        carrier=doc.get("carrier", None),
        estimated_delivery=doc.get("estimated_delivery", None),
        total_events=len(updates),
        tracking_updates=[TrackingEvent(**e) for e in updates],
    )
