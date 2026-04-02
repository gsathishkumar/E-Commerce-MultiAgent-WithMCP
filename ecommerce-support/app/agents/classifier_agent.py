"""
Classifier Agent  —  LLM-based semantic router
───────────────────────────────────────────────
Uses 'openai_model' to classify the customer query into one of four intents.
No keyword matching — purely semantic reasoning by the LLM.

Intents
  • product_catalog  – pricing, specs, stock, warranty, ratings, delivery ETA
  • refund_policy    – return/refund/exchange rules, eligibility, timelines
  • orders_db        – order status, order details, shipment tracking
  • refunds_db       – refund / return request status for a specific order or return ID
"""

import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.schema.state import SupportState
from app.core.settings import settings

_CLASSIFIER_SYSTEM = """You are an expert customer-support query router for an e-commerce platform.

Your ONLY job is to classify the customer's query into exactly one of these four agent categories:

1. product_catalog
   Handles: product pricing, specifications, stock availability, warranty details,
   customer ratings, delivery timelines for items not yet purchased.

2. refund_policy
   Handles: general return/refund/exchange policies, eligibility rules, return windows,
   non-returnable categories, refund processing methods, pickup logistics, escalation paths.

3. orders_db
   Handles: status of a specific order the customer already placed, order details,
   shipment tracking, carrier information, delivery updates.

4. refunds_db
   Handles: status of an existing return or refund request, details of a specific
   return/refund case, multiple return requests for an order.

Respond ONLY with a JSON object — no prose, no markdown fences:
{
  "intent": "<one of the four intents above>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one-sentence explanation>"
}
"""


def classifier_agent(state: SupportState) -> SupportState:
    """Classify the customer query and populate intent fields in state."""
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        max_tokens=256,
        temperature=0,
    )

    messages = [
        SystemMessage(content=_CLASSIFIER_SYSTEM),
        HumanMessage(content=f"Customer query: {state['customer_query']}"),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
        if raw.startswith("```"):  # if the model wrapped its JSON in Markdown code fences.
            raw = "\n".join(raw.split("\n")[1:-1]) # strips the first and last lines (the ``` fence markers)
        parsed = json.loads(raw)

        return {
            **state,
            "intent": parsed["intent"],
            "routing_confidence": parsed.get("confidence", 0.0),
            "routing_reasoning": parsed.get("reasoning", ""),
        }
    except Exception as exc:
        return {
            **state,
            "intent": "product_catalog",
            "routing_confidence": 0.0,
            "routing_reasoning": "Classification failed; defaulting to product_catalog.",
            "error": str(exc),
        }
