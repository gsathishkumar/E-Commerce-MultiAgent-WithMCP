"""
app/routes/order_routes.py

Two REST endpoints for the Orders API.
"""

from fastapi import APIRouter

from app.schemas.order_schemas import OrderResponse, TrackingResponse
from app.services.order_service import get_order_details, get_order_tracking

router = APIRouter(prefix="/orders", tags=["Orders"])


# ---------------------------------------------------------------------------
# Endpoint 1 — Order Details
# ---------------------------------------------------------------------------

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order details",
    responses={
        200: {"description": "Order found and returned successfully."},
        404: {"description": "Order not found."},
    },
)
async def fetch_order_details(order_id: str) -> OrderResponse:
    """
    **Endpoint 1 — Order Details**

    Returns the full order document for the given `order_id`.

    **Flow:**
    `Route` → `get_order_details()` → `Tool: lookup_order()` → MongoDB `orders`

    | Code | Meaning |
    |------|---------|
    | 200 | Order document returned |
    | 404 | No order with that ID |
    """
    return await get_order_details(order_id)


# ---------------------------------------------------------------------------
# Endpoint 2 — Tracking History
# ---------------------------------------------------------------------------

@router.get(
    "/{order_id}/tracking",
    response_model=TrackingResponse,
    summary="Get order tracking history",
    responses={
        200: {"description": "Tracking history returned successfully."},
        404: {"description": "Order not found."},
    },
)
async def fetch_order_tracking(order_id: str) -> TrackingResponse:
    """
    **Endpoint 2 — Tracking History**

    Returns carrier metadata and the full list of tracking events for
    the given `order_id`, in chronological order.

    **Flow:**
    `Route` → `get_order_tracking()` → `Tool: get_tracking_updates()` → MongoDB `orders`

    | Code | Meaning |
    |------|---------|
    | 200 | Tracking events returned |
    | 404 | No order with that ID |
    """
    return await get_order_tracking(order_id)
