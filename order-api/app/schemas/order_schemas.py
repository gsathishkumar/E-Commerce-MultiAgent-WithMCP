"""
app/schemas/order_schemas.py

Pydantic models that mirror the exact shape of the `orders` MongoDB
collection.  Every field name, type, and example matches the real data.
"""
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class TrackingEvent(BaseModel):
    """A single step in the shipment journey."""

    date: str = Field(..., description="Date of the event (YYYY-MM-DD).")
    status: str = Field(..., description="Human-readable status label.")
    location: str = Field(default="", description="Location at the time of the event.")

    model_config = {"json_schema_extra": {
        "example": {
            "date": "2026-03-11",
            "status": "In transit",
            "location": "Pune Hub",
        }
    }}


# ---------------------------------------------------------------------------
# Endpoint 1 — Order Details
# ---------------------------------------------------------------------------

class OrderResponse(BaseModel):
    """
    Full order document returned by
    GET /api/v1/orders/{order_id}
    """

    order_id: str = Field(..., description="Unique order identifier.")
    customer_name: str = Field(..., description="Full name of the customer.")
    customer_email: str = Field(..., description="Customer email address.")
    product_id: str = Field(..., description="SKU / product identifier.")
    product_name: str = Field(..., description="Human-readable product name.")
    quantity: int = Field(..., description="Number of units ordered.")
    total_amount: float = Field(..., description="Total order value in INR.")
    order_date: str = Field(..., description="Date the order was placed (YYYY-MM-DD).")
    status: str = Field(..., description="Current order status.")
    
    # Optional Fields
    tracking_id: Optional[str] =  Field(None, description="Carrier tracking reference.")
    carrier: Optional[str] = Field(None , description="Logistics carrier name.")
    estimated_delivery: Optional[str] = Field(None, description="Expected delivery date (YYYY-MM-DD).")
    shipping_address: Optional[str] = Field(None, description="Full shipping address.")
    payment_method: Optional[str] = Field(None, description="Payment method used.")
    delivered_date: Optional[str] = Field(None, description="Delivery date.")
    cancellation_reason : Optional[str] = Field(None, description="Reason for Cancellation")
    refund_status : Optional[str] = Field(None, description="Status of Refund")
    refund_amount : Optional[int] = Field(None, description="Refunded Amount")
    refund_date : Optional[str] = Field(None, description="Date of Refund")

    model_config = {"json_schema_extra": {
        "example": {
            "order_id": "ORD-10001",
            "customer_name": "Rahul Verma",
            "customer_email": "rahul.verma@wipro.com",
            "product_id": "PROD-001",
            "product_name": "MacBook Air M3 15-inch",
            "quantity": 1,
            "total_amount": 134900,
            "order_date": "2026-03-08",
            "status": "shipped",
            "tracking_id": "DELHIVERY-8834521",
            "carrier": "Delhivery",
            "estimated_delivery": "2026-03-14",
            "shipping_address": "42, Koramangala 4th Block, Bangalore 560034",
            "payment_method": "Credit Card (HDFC)",
        }
    }}


# ---------------------------------------------------------------------------
# Endpoint 2 — Tracking History
# ---------------------------------------------------------------------------

class TrackingResponse(BaseModel):
    """
    Tracking history returned by
    GET /api/v1/orders/{order_id}/tracking
    """

    order_id: str = Field(..., description="Unique order identifier.")
    tracking_id: Optional[str] = Field(None, description="Carrier tracking reference.")
    carrier: Optional[str] = Field(None, description="Logistics carrier name.")
    estimated_delivery: Optional[str] = Field(None, description="Expected delivery date (YYYY-MM-DD).")
    total_events: int = Field(..., description="Number of tracking events.")
    tracking_updates: list[TrackingEvent] = Field(
        ..., description="Ordered list of tracking events (oldest first)."
    )

    model_config = {"json_schema_extra": {
        "example": {
            "order_id": "ORD-10001",
            "tracking_id": "DELHIVERY-8834521",
            "carrier": "Delhivery",
            "estimated_delivery": "2026-03-14",
            "total_events": 6,
            "tracking_updates": [
                {"date": "2026-03-08", "status": "Order placed", "location": ""},
                {"date": "2026-03-09", "status": "Packed", "location": "Mumbai Warehouse"},
                {"date": "2026-03-10", "status": "Shipped", "location": "Mumbai Warehouse"},
                {"date": "2026-03-11", "status": "In transit", "location": "Pune Hub"},
                {"date": "2026-03-12", "status": "In transit", "location": "Bangalore Hub"},
                {"date": "2026-03-13", "status": "Out for delivery", "location": "Koramangala"},
            ],
        }
    }}
