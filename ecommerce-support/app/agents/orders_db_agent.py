"""
Orders DB Agent

Tool 1: MCP tool `get_order_details`
        Returns the full order document from MongoDB.

Tool 2: MCP tool `get_order_tracking_history`
        Returns carrier metadata and the full list of tracking events
        for the given order_id, in chronological order.

Both tool responses are serialized to JSON and injected into a single
LLM prompt to produce the final natural-language answer.
"""

import asyncio
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent

from app.core.settings import settings
from app.schema.state import SupportState

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


def _decode_mcp_result(result) -> dict:
    """Prefer structured MCP output and fall back to JSON text content."""
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured

    for content in getattr(result, "content", []):
        if isinstance(content, TextContent):
            try:
                return json.loads(content.text)
            except json.JSONDecodeError:
                return {"message": content.text}

    return {"error": "MCP tool returned no usable content."}


async def _fetch_order_tool_data(order_id: str) -> dict:
    tool_data: dict = {}

    async with streamable_http_client(settings.order_mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            try:
                order_result = await session.call_tool(
                    "get_order_details",
                    arguments={"order_id": order_id},
                )
                tool_data["order"] = _decode_mcp_result(order_result)
            except Exception as exc:
                tool_data["order"] = {"error": str(exc)}

            try:
                tracking_result = await session.call_tool(
                    "get_order_tracking_history",
                    arguments={"order_id": order_id},
                )
                tool_data["tracking"] = _decode_mcp_result(tracking_result)
            except Exception as exc:
                tool_data["tracking"] = {"error": str(exc)}

    return tool_data


def orders_db_agent(state: SupportState) -> SupportState:
    """Fetch order + tracking data via MCP then generate a natural-language response."""
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

    try:
        tool_data = asyncio.run(_fetch_order_tool_data(order_id))
    except Exception as exc:
        tool_data = {
            "order": {"error": str(exc)},
            "tracking": {"error": str(exc)},
        }

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
