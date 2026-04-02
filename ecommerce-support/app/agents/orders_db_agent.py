"""
Orders DB Agent
───────────────
Tool 1: GET http://localhost:8003/order-api/api/v1/orders/{order_id}
        Returns the full order document from MongoDB.

Tool 2: GET http://localhost:8003/order-api/api/v1/orders/{order_id}/tracking
        Returns carrier metadata and the full list of tracking events
        for the given order_id, in chronological order.

Both tool responses are serialised to JSON and injected into a single
'openai_model' prompt to produce the final natural-language answer.
"""

import re
import json
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.schema.state import SupportState
from app.core.settings import settings

_AGENT_SYSTEM = """You are an order management specialist. You have access to real-time order
and shipment data retrieved from the database.

Using the order details and tracking information provided below, answer the customer's question
accurately. Include relevant facts such as order status, items ordered, payment details,
current shipment location, estimated delivery date, or recent tracking events.

Be precise about dates and statuses. Do not speculate beyond the data provided.
If an order ID could not be found, apologise and ask the customer to verify the order number.
"""

_ORDER_ID_RE = re.compile(r"\bORD[-–]?\d{4,8}\b", re.IGNORECASE)


def _extract_order_id(query: str) -> str | None:
    match = _ORDER_ID_RE.search(query)
    return match.group(0).upper().replace("–", "-") if match else None


def orders_db_agent(state: SupportState) -> SupportState:
    """Fetch order + tracking data then generate a natural-language response."""
    query = state["customer_query"]
    order_id = _extract_order_id(query)

    if not order_id:
        return {
            **state,
            "specialist_response": (
                "I'd be happy to help with your order! Could you please share your "
                "Order ID (it looks like ORD-XXXXX) so I can pull up the details?"
            ),
        }

    tool_data: dict = {}

    # ── Tool 1: Full order document ──────────────────────────────────────────
    try:
        resp = httpx.get(f"{settings.order_api_url}/{order_id}", timeout=15)
        resp.raise_for_status()
        tool_data["order"] = resp.json()
    except httpx.HTTPStatusError as exc:
        tool_data["order"] = {"error": exc.response.text}
    except Exception as exc:
        tool_data["order"] = {"error": str(exc)}

    # ── Tool 2: Tracking history ─────────────────────────────────────────────
    try:
        resp = httpx.get(f"{settings.order_api_url}/{order_id}/tracking", timeout=15)
        resp.raise_for_status()
        tool_data["tracking"] = resp.json()
    except httpx.HTTPStatusError as exc:
        tool_data["tracking"] = {"error": exc.response.text}
    except Exception as exc:
        tool_data["tracking"] = {"error": str(exc)}

    # ── LLM: Synthesise response ─────────────────────────────────────────────
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        max_tokens=1024,
        temperature=0.1,
    )

    messages = [
        SystemMessage(content=_AGENT_SYSTEM),
        HumanMessage(
            content=(
                f"ORDER & TRACKING DATA:\n{json.dumps(tool_data, indent=2)}\n\n"
                f"CUSTOMER QUESTION: {query}"
            )
        ),
    ]

    try:
        response = llm.invoke(messages)
        return {**state, "specialist_response": response.content}
    except Exception as exc:
        return {
            **state,
            "specialist_response": "I was unable to retrieve order information at this time.",
            "error": str(exc),
        }
