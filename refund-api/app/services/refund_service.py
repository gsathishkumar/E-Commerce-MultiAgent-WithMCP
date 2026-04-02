"""
app/services/refund_service.py

Service layer — business logic between the API routes and the tools.
Validates existence, assembles typed Pydantic responses.
"""

from fastapi import HTTPException, status

from app.schemas.refund_schemas import (
    ReturnResponse,
    ReturnSummary,
    ReturnsByOrderResponse,
)
from app.tools.refund_tools import get_return_by_order, lookup_return


# ---------------------------------------------------------------------------
# Service 1 — fetch a single return by return_id
# ---------------------------------------------------------------------------

async def get_return_details(return_id: str) -> ReturnResponse:
    """
    Fetch the full return document for *return_id*.

    Raises:
        HTTPException 404 — when no document matches ``return_id``.
    """
    doc = await lookup_return(return_id)

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return request '{return_id}' not found.",
        )

    return ReturnResponse(**doc)


# ---------------------------------------------------------------------------
# Service 2 — fetch all returns for an order
# ---------------------------------------------------------------------------

async def get_returns_for_order(order_id: str) -> ReturnsByOrderResponse:
    """
    Fetch all return requests linked to *order_id*.

    Returns an empty ``returns`` list (not a 404) when the order exists
    but has no returns — callers can distinguish "order not found" from
    "no returns for this order" via the ``total_returns`` field.

    Raises:
        HTTPException 404 — when no return documents exist for this order.
    """
    docs = await get_return_by_order(order_id)

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No return requests found for order '{order_id}'.",
        )

    # All documents for the same order share the same customer_name
    customer_name = docs[0].get("customer_name", "")

    summaries = [
        ReturnSummary(
            return_id=doc["return_id"],
            product_name=doc["product_name"],
            reason=doc["reason"],
            request_date=doc["request_date"],
            status=doc["status"],
            resolution_type=doc["resolution_type"],
            refund_amount=doc["refund_amount"],
            refund_status=doc["refund_status"],
            eligible=doc["eligible"],
        )
        for doc in docs
    ]

    return ReturnsByOrderResponse(
        order_id=order_id,
        customer_name=customer_name,
        total_returns=len(summaries),
        returns=summaries,
    )
