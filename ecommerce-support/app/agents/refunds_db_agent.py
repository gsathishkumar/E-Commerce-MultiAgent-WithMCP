"""
Refunds DB Agent

Tool 1: MCP tool `get_return_details`
        Returns the full return/refund document for the given return_id.

Tool 2: MCP tool `get_all_returns_by_order`
        Returns all return requests linked to the given order_id,
        with a summary of each return sorted oldest-first.

The agent extracts whichever ID is present in the query (return_id takes
priority; falls back to order_id), calls the matching tool(s), and passes
both responses to 'openai_model' for a natural-language answer.
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

_AGENT_SYSTEM = """You are a refunds and returns specialist. You have access to real-time
return and refund data retrieved from the database.

Using the return/refund information provided, answer the customer's question clearly.
Cover return status, refund amount, refund method, expected credit timelines, pickup details,
or any relevant notes from the system.

Be empathetic and proactive - if a refund is expected soon, reassure the customer.
If data shows an issue, acknowledge it and suggest next steps.
"""

_RETURN_ID_RE = re.compile(r"\bRET[-–]?\d{4,8}\b", re.IGNORECASE)
_ORDER_ID_RE = re.compile(r"\bORD[-–]?\d{4,8}\b", re.IGNORECASE)


def _extract_ids(query: str) -> tuple[str | None, str | None]:
    ret = _RETURN_ID_RE.search(query)
    ord_ = _ORDER_ID_RE.search(query)
    return (
        ret.group(0).upper().replace("–", "-") if ret else None,
        ord_.group(0).upper().replace("–", "-") if ord_ else None,
    )


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


async def _fetch_refund_tool_data(return_id: str | None, order_id: str | None) -> dict:
    tool_data: dict = {}

    async with streamable_http_client(settings.refund_mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if return_id:
                try:
                    return_result = await session.call_tool(
                        "get_return_details",
                        arguments={"return_id": return_id},
                    )
                    tool_data["return_document"] = _decode_mcp_result(return_result)
                except Exception as exc:
                    tool_data["return_document"] = {"error": str(exc)}

            if order_id:
                try:
                    order_result = await session.call_tool(
                        "get_all_returns_by_order",
                        arguments={"order_id": order_id},
                    )
                    tool_data["returns_for_order"] = _decode_mcp_result(order_result)
                except Exception as exc:
                    tool_data["returns_for_order"] = {"error": str(exc)}

    return tool_data


def refunds_db_agent(state: SupportState) -> SupportState:
    """Fetch return/refund data via MCP then generate a natural-language response."""
    query = state["customer_query"]
    return_id, order_id = _extract_ids(query)

    if not return_id and not order_id:
        return {
            **state,
            "specialist_response": (
                "I'd be happy to check on your return or refund! "
                "Could you please share your Return ID (RET-XXXXX) "
                "or Order ID (ORD-XXXXX)?"
            ),
        }

    try:
        tool_data = asyncio.run(_fetch_refund_tool_data(return_id, order_id))
    except Exception as exc:
        tool_data = {}
        if return_id:
            tool_data["return_document"] = {"error": str(exc)}
        if order_id:
            tool_data["returns_for_order"] = {"error": str(exc)}

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
                f"RETURN/REFUND DATA:\n{json.dumps(tool_data, indent=2)}\n\n"
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
            "specialist_response": "I was unable to retrieve refund information at this time.",
            "error": str(exc),
        }
