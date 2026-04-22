"""
Product Catalog RAG Agent
─────────────────────────
Tool   : MCP tool `get_product_chunks_by_query`
Flow   : Call tool → inject chunks into prompt → 'openai_model' generates grounded answer.
"""

import asyncio
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent

from app.schema.state import SupportState
from app.core.settings import settings

_AGENT_SYSTEM = """You are a knowledgeable product specialist for a premium e-commerce store.

Using ONLY the product information provided in the context below, answer the customer's question
accurately and helpfully. Include relevant details such as price, specifications, stock status,
warranty, ratings, and delivery timelines when applicable.

If the context does not contain enough information to fully answer the question, say so clearly
and suggest the customer check the website or contact support for the most up-to-date details.

Do NOT invent product details. Be precise and friendly.
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


async def _fetch_product_chunks(query: str) -> dict:
    async with streamable_http_client(settings.product_mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_product_chunks_by_query",
                arguments={"query": query, "top_k": 3},
            )
            return _decode_mcp_result(result)


def product_catalog_agent(state: SupportState) -> SupportState:
    """RAG agent for product catalog queries."""
    query = state["customer_query"]

    # ── Step 1: Retrieve context chunks from the MCP tool ────────────────────
    context = ""
    try:
        response_json = asyncio.run(_fetch_product_chunks(query))
        parts = []
        for i, chunk in enumerate(response_json.get("results", [])):
            text = chunk.get("text")
            parts.append(f"[Product context {i + 1}]\n{text}")
        context = "\n\n".join(parts)
    except Exception as exc:
        context = "(Product catalog service unavailable.)"
        state = {**state, "error": str(exc)}

    # ── Step 2: Generate grounded answer via 'openai_model' ────────────────────
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        max_tokens=1024,
        temperature=0.2,
    )

    messages = [
        SystemMessage(content=_AGENT_SYSTEM),
        HumanMessage(
            content=f"PRODUCT CONTEXT:\n{context}\n\nCUSTOMER QUESTION: {query}"
        ),
    ]

    try:
        response = llm.invoke(messages)
        return {**state, "specialist_response": response.content}
    except Exception as exc:
        return {
            **state,
            "specialist_response": "I was unable to retrieve product information at this time.",
            "error": str(exc),
        }
