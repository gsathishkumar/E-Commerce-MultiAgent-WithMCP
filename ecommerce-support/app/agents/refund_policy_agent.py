"""
Refund Policy RAG Agent
Tool   : MCP tool `get_refund_chunks_by_query`
Flow   : Call tool -> inject chunks into prompt -> 'openai_model' generates grounded answer.
"""

import asyncio
import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent

from app.core.settings import settings
from app.schema.state import SupportState

_AGENT_SYSTEM = """You are a customer support specialist well-versed in the store's return,
refund, and exchange policies.

Using ONLY the policy information provided in the context below, answer the customer's question
thoroughly. Cover return windows, eligibility, refund methods, timelines, and any relevant
conditions or exceptions.

If the policy context does not cover the customer's specific situation, clearly say so and
direct them to contact support for a personalised assessment.

Be empathetic, clear, and reassuring.
"""


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


async def _fetch_refund_policy_chunks(query: str) -> dict:
    async with streamable_http_client(settings.refund_policy_mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_refund_chunks_by_query",
                arguments={"query": query, "top_k": 4},
            )
            return _decode_mcp_result(result)


def refund_policy_agent(state: SupportState) -> SupportState:
    """RAG agent for refund/return/exchange policy queries."""
    query = state["customer_query"]

    context = ""
    try:
        response_json = asyncio.run(_fetch_refund_policy_chunks(query))
        parts = []
        for i, chunk in enumerate(response_json.get("results", [])):
            text = chunk.get("text")
            parts.append(f"[Policy section {i + 1}]\n{text}")
        context = "\n\n".join(parts)
    except Exception as exc:
        context = "(Refund policy service unavailable.)"
        state = {**state, "error": str(exc)}

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        max_tokens=1024,
        temperature=0.2,
    )

    messages = [
        SystemMessage(content=_AGENT_SYSTEM),
        HumanMessage(
            content=f"POLICY CONTEXT:\n{context}\n\nCUSTOMER QUESTION: {query}"
        ),
    ]

    try:
        response = llm.invoke(messages)
        return {**state, "specialist_response": response.content}
    except Exception as exc:
        return {
            **state,
            "specialist_response": "I was unable to retrieve policy information at this time.",
            "error": str(exc),
        }
