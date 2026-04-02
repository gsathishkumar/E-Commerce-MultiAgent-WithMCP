"""
app/schemas/refund_schemas.py

Pydantic models that mirror the exact shape of the `refunds` MongoDB
collection.  Optional fields (pickup_date, notes, replacement_order_id)
are typed accordingly.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Endpoint 1 — Lookup by return_id
# ---------------------------------------------------------------------------

class ReturnResponse(BaseModel):
    """
    Full return/refund document returned by
    GET /api/v1/refunds/return/{return_id}
    """

    return_id: str = Field(..., description="Unique return request identifier.")
    order_id: str = Field(..., description="Original order this return is linked to.")
    customer_name: str = Field(..., description="Full name of the customer.")
    product_name: str = Field(..., description="Name of the product being returned.")
    reason: str = Field(..., description="Customer-stated reason for the return.")
    request_date: str = Field(..., description="Date the return was requested (YYYY-MM-DD).")
    status: str = Field(..., description="Current return status.")
    pickup_date: Optional[str] = Field(None, description="Scheduled pickup date, if set.")
    refund_method: str = Field(..., description="Method via which refund will be issued.")
    refund_amount: float = Field(..., description="Refund amount in INR.")
    refund_status: str = Field(..., description="Current refund processing status.")
    resolution_type: str = Field(..., description="Resolution: refund | replacement | exchange.")
    replacement_order_id: Optional[str] = Field(None, description="New order ID if resolution is replacement.")
    return_policy_days: int = Field(..., description="Return window in days per policy.")
    eligible: bool = Field(..., description="Whether the return is within policy eligibility.")
    notes: Optional[str] = Field(None, description="Internal notes or instructions.")

    model_config = {"json_schema_extra": {
        "example": {
            "return_id": "RET-3001",
            "order_id": "ORD-10002",
            "customer_name": "Sneha Patel",
            "product_name": "Sony WH-1000XM5 Headphones",
            "reason": "Defective - Left ear cup not producing sound",
            "request_date": "2026-03-10",
            "status": "pickup_scheduled",
            "pickup_date": "2026-03-15",
            "refund_method": "Original payment method (UPI)",
            "refund_amount": 24990,
            "refund_status": "pending",
            "resolution_type": "replacement",
            "replacement_order_id": "ORD-10005",
            "return_policy_days": 7,
            "eligible": True,
            "notes": None,
        }
    }}


# ---------------------------------------------------------------------------
# Endpoint 2 — Lookup by order_id  (may have multiple returns per order)
# ---------------------------------------------------------------------------

class ReturnSummary(BaseModel):
    """
    Compact summary of a single return, used inside the list response.
    Includes the most actionable fields without lower-priority detail.
    """

    return_id: str = Field(..., description="Unique return request identifier.")
    product_name: str = Field(..., description="Product being returned.")
    reason: str = Field(..., description="Reason for return.")
    request_date: str = Field(..., description="Date the return was requested (YYYY-MM-DD).")
    status: str = Field(..., description="Current return status.")
    resolution_type: str = Field(..., description="Resolution type: refund | replacement | exchange.")
    refund_amount: float = Field(..., description="Refund amount in INR.")
    refund_status: str = Field(..., description="Current refund processing status.")
    eligible: bool = Field(..., description="Return policy eligibility flag.")


class ReturnsByOrderResponse(BaseModel):
    """
    All return requests linked to an order, returned by
    GET /api/v1/refunds/order/{order_id}
    """

    order_id: str = Field(..., description="The order being queried.")
    customer_name: str = Field(..., description="Customer associated with the order.")
    total_returns: int = Field(..., description="Number of return requests found.")
    returns: list[ReturnSummary] = Field(
        ..., description="List of return requests for this order."
    )

    model_config = {"json_schema_extra": {
        "example": {
            "order_id": "ORD-10001",
            "customer_name": "Rahul Verma",
            "total_returns": 1,
            "returns": [
                {
                    "return_id": "RET-3002",
                    "product_name": "MacBook Air M3 15-inch",
                    "reason": "Not satisfied with performance",
                    "request_date": "2026-03-14",
                    "status": "evaluation",
                    "resolution_type": "refund",
                    "refund_amount": 134900,
                    "refund_status": "pending",
                    "eligible": True,
                }
            ],
        }
    }}
