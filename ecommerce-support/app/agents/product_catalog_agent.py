"""
Product Catalog RAG Agent
─────────────────────────
Tool   : GET http://localhost:8001/product-rag/api/v1/retrieve
Flow   : Call tool → inject chunks into prompt → 'openai_model' generates grounded answer.

Query params  : ?query=<customer query>&top_k=3
Expected resp : list of { "id": "...", "content": "..." }  (or any JSON the server returns)
"""

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
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


def product_catalog_agent(state: SupportState) -> SupportState:
    """RAG agent for product catalog queries."""
    query = state["customer_query"]

    # ── Step 1: Retrieve context chunks from Docker tool endpoint ────────────
    context = ""
    try:
        resp = httpx.get(
            settings.product_rag_url,
            params={"query": query, "top_k": 3},
            timeout=15,
        )
        resp.raise_for_status()
        response_json = resp.json()
        parts = [] # All chunks are accumulated here
        for i, chunk in enumerate(response_json['results']):
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
