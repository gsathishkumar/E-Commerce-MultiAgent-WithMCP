"""
Refund Policy RAG Agent
───────────────────────
Tool   : GET http://localhost:8002/refund-rag/api/v1/retrieve
Flow   : Call tool → inject chunks into prompt → 'openai_model' generates grounded answer.

Query params  : ?query=<customer query>&top_k=4
Expected resp : list of { "id": "...", "content": "..." }  (or any JSON the server returns)
"""

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.schema.state import SupportState
from app.core.settings import settings

_AGENT_SYSTEM = """You are a customer support specialist well-versed in the store's return,
refund, and exchange policies.

Using ONLY the policy information provided in the context below, answer the customer's question
thoroughly. Cover return windows, eligibility, refund methods, timelines, and any relevant
conditions or exceptions.

If the policy context does not cover the customer's specific situation, clearly say so and
direct them to contact support for a personalised assessment.

Be empathetic, clear, and reassuring.
"""


def refund_policy_agent(state: SupportState) -> SupportState:
    """RAG agent for refund/return/exchange policy queries."""
    query = state["customer_query"]

    # ── Step 1: Retrieve context chunks from Docker tool endpoint ────────────
    context = ""
    try:
        resp = httpx.get(
            settings.refund_policy_rag_url,
            params={"query": query, "top_k": 4},
            timeout=15,
        )
        resp.raise_for_status()
        response_json = resp.json()
        parts = [] # All chunks are accumulated here
        for i, chunk in enumerate(response_json['results']):
            text = chunk.get("text")
            parts.append(f"[Policy section {i + 1}]\n{text}")
        context = "\n\n".join(parts)
    except Exception as exc:
        context = "(Refund policy service unavailable.)"
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
