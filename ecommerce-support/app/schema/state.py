"""
Shared state schema passed through the LangGraph workflow.
"""
from typing import Optional
from typing_extensions import TypedDict


class SupportState(TypedDict):
    # Input
    customer_query: str

    # Routing
    intent: Optional[str]           # e.g. "product_catalog", "refund_policy", "orders_db", "refunds_db"
    routing_confidence: Optional[float]
    routing_reasoning: Optional[str]

    # Specialist agent output (raw)
    specialist_response: Optional[str]

    # Final synthesised customer-facing response
    final_response: Optional[str]

    # Error propagation
    error: Optional[str]
