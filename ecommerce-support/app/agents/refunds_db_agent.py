"""
Refunds DB Agent
────────────────
Tool 1: GET http://localhost:8004/refund-api/api/v1/refunds/return/{return_id}
        Returns the full return/refund document for the given return_id.

Tool 2: GET http://localhost:8004/refund-api/api/v1/refunds/order/{order_id}
        Returns all return requests linked to the given order_id,
        with a summary of each return sorted oldest-first.

The agent extracts whichever ID is present in the query (return_id takes
priority; falls back to order_id), calls the matching tool(s), and passes
both responses to 'openai_model' for a natural-language answer.
"""

import re
import json
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.schema.state import SupportState
from app.core.settings import settings

_AGENT_SYSTEM = """You are a refunds and returns specialist. You have access to real-time
return and refund data retrieved from the database.

Using the return/refund information provided, answer the customer's question clearly.
Cover return status, refund amount, refund method, expected credit timelines, pickup details,
or any relevant notes from the system.

Be empathetic and proactive — if a refund is expected soon, reassure the customer.
If data shows an issue, acknowledge it and suggest next steps.
"""

_RETURN_ID_RE = re.compile(r"\bRET[-–]?\d{4,8}\b", re.IGNORECASE)
_ORDER_ID_RE  = re.compile(r"\bORD[-–]?\d{4,8}\b", re.IGNORECASE)


def _extract_ids(query: str) -> tuple[str | None, str | None]:
    ret = _RETURN_ID_RE.search(query)
    ord_ = _ORDER_ID_RE.search(query)
    return (
        ret.group(0).upper().replace("–", "-") if ret else None,
        ord_.group(0).upper().replace("–", "-") if ord_ else None,
    )


def refunds_db_agent(state: SupportState) -> SupportState:
    """Fetch return/refund data then generate a natural-language response."""
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

    tool_data: dict = {}

    # ── Tool 1: Specific return document ─────────────────────────────────────
    if return_id:
        try:
            resp = httpx.get(f"{settings.refund_api_url}/return/{return_id}", timeout=15)
            resp.raise_for_status()
            tool_data["return_document"] = resp.json()
        except httpx.HTTPStatusError as exc:
            tool_data["return_document"] = {"error": exc.response.text}
        except Exception as exc:
            tool_data["return_document"] = {"error": str(exc)}

    # ── Tool 2: All returns for an order ─────────────────────────────────────
    if order_id:
        try:
            resp = httpx.get(f"{settings.refund_api_url}/order/{order_id}", timeout=15)
            resp.raise_for_status()
            tool_data["returns_for_order"] = resp.json()
        except httpx.HTTPStatusError as exc:
            tool_data["returns_for_order"] = {"error": exc.response.text}
        except Exception as exc:
            tool_data["returns_for_order"] = {"error": str(exc)}

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
