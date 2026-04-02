"""
Response Synthesizer Agent
──────────────────────────
Final node in every workflow path. Takes the specialist agent's raw output
and the original customer query, then:

  1. Rewrites the response to be polite, professional, jargon-free,
     and customer-friendly.
  2. Validates that the response actually addresses the customer's query.
  3. ADDs a support escalation note if the response appears incomplete
     or off-topic.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.schema.state import SupportState
from app.core.settings import settings

_SYNTHESIZER_SYSTEM = """You are a senior customer experience writer for a premium e-commerce platform.

Your task:
1. REWRITE the specialist agent's draft response so that it is:
   - Warm, polite, and professional (never cold or robotic)
   - Free of internal jargon, system IDs, technical field names, or database language
   - Well-formatted with short paragraphs or bullet points where helpful
   - Actionable — the customer should know exactly what to expect or do next

2. VALIDATE relevance: Decide if the response genuinely addresses the customer's
   original question.
   - If it does, output the polished response as-is.
   - If the specialist response is incomplete, vague, or off-topic, Don't guess any text and 
     ONLY add the following note:

     "If you need further assistance with this, our support team is always here
      to help. You can reach us via chat, email at support@store.in, or call
      1800-XXX-XXXX (available 9 AM – 9 PM, 7 days a week)."

3. Always begin with a brief warm greeting that acknowledges the customer's concern.
4. Always end with a short positive closing (e.g., "Happy shopping!" or
   "We're here if you need us.").
5. NEVER reveal internal system details, agent names, tool outputs, confidence
   scores, or raw JSON.
"""


def synthesizer_agent(state: SupportState) -> SupportState:
    """Polish and validate the specialist's response into a customer-ready reply."""
    query = state["customer_query"]
    draft = state.get("specialist_response") or "No response was generated."

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        max_tokens=1500,
        temperature=0,
    )

    messages = [
        SystemMessage(content=_SYNTHESIZER_SYSTEM),
        HumanMessage(
            content=(
                f"ORIGINAL CUSTOMER QUESTION:\n{query}\n\n"
                f"SPECIALIST DRAFT RESPONSE:\n{draft}\n\n"
                "Please produce the final customer-facing response."
            )
        ),
    ]

    try:
        response = llm.invoke(messages)
        return {**state, "final_response": response.content}
    except Exception as exc:
        fallback = (
            f"Thank you for reaching out!\n\n{draft}\n\n"
            "If you need further help, please contact us at support@store.in "
            "or call 1800-XXX-XXXX (9 AM–9 PM)."
        )
        return {
            **state,
            "final_response": fallback,
            "error": str(exc),
        }
