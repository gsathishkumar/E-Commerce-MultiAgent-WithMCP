"""
app/routes/refund_routes.py

Two REST endpoints for the Refunds API.
"""

from fastapi import APIRouter

from app.schemas.refund_schemas import ReturnResponse, ReturnsByOrderResponse
from app.services.refund_service import get_return_details, get_returns_for_order

router = APIRouter(prefix="/refunds", tags=["Refunds"])


# ---------------------------------------------------------------------------
# Endpoint 1 — lookup by return_id
# ---------------------------------------------------------------------------

@router.get(
    "/return/{return_id}",
    response_model=ReturnResponse,
    summary="Get return details by return ID",
    responses={
        200: {"description": "Return document found and returned successfully."},
        404: {"description": "Return request not found."},
    },
)
async def fetch_return_details(return_id: str) -> ReturnResponse:
    """
    **Endpoint 1 — Return Details**

    Returns the full return/refund document for the given `return_id`.

    **Flow:**
    `Route` → `get_return_details()` → `Tool: lookup_return()` → MongoDB `refunds`

    | Code | Meaning |
    |------|---------|
    | 200  | Return document returned |
    | 404  | No return with that ID   |
    """
    return await get_return_details(return_id)


# ---------------------------------------------------------------------------
# Endpoint 2 — lookup all returns for an order
# ---------------------------------------------------------------------------

@router.get(
    "/order/{order_id}",
    response_model=ReturnsByOrderResponse,
    summary="Get all return requests for an order",
    responses={
        200: {"description": "Return requests found and returned successfully."},
        404: {"description": "No return requests found for this order."},
    },
)
async def fetch_returns_by_order(order_id: str) -> ReturnsByOrderResponse:
    """
    **Endpoint 2 — Returns by Order**

    Returns all return requests linked to the given `order_id`, with a
    summary of each return sorted oldest-first.

    **Flow:**
    `Route` → `get_returns_for_order()` → `Tool: get_return_by_order()` → MongoDB `refunds`

    | Code | Meaning |
    |------|---------|
    | 200  | Return list returned                    |
    | 404  | No return requests exist for this order |
    """
    return await get_returns_for_order(order_id)
