"""
LangGraph Multi-Agent Customer Support Workflow
────────────────────────────────────────────────
Architecture: Router Pattern

           ┌─────────────────────────────────────────┐
           │           Customer Query                 │
           └──────────────┬──────────────────────────┘
                          │
                          ▼
               ┌──────────────────┐
               │  Classifier Agent│  (LLM-based semantic routing)
               └──────┬───────────┘
                      │ intent
          ┌───────────┼──────────────┬──────────────┐
          ▼           ▼              ▼               ▼
  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
  │ Product   │ │ Refund   │ │ Orders   │ │  Refunds DB  │
  │ Catalog   │ │ Policy   │ │ DB Agent │ │    Agent     │
  │ RAG Agent │ │ RAG Agent│ │          │ │              │
  └─────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘
        │             │            │               │
        └─────────────┴────────────┴───────────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │  Synthesizer Agent     │
                   │  (polish + validate)   │
                   └────────────────────────┘
                                │
                                ▼
                       Final Response
"""

from langgraph.graph import StateGraph, END
from app.schema.state import SupportState
from app.agents.classifier_agent import classifier_agent
from app.agents.product_catalog_agent import product_catalog_agent
from app.agents.refund_policy_agent import refund_policy_agent
from app.agents.orders_db_agent import orders_db_agent
from app.agents.refunds_db_agent import refunds_db_agent
from app.agents.synthesizer_agent import synthesizer_agent


# ── Router function (pure Python, reads LLM-set intent) ─────────────────────

def route_to_specialist(state: SupportState) -> str:
    """
    Conditional edge: maps the LLM-assigned intent to the correct specialist node.
    This is NOT keyword matching — the intent was determined by LLM.
    """
    intent = state.get("intent", "product_catalog")
    routing_map = {
        "product_catalog": "route_to_product_catalog_agent",
        "refund_policy":   "route_to_refund_policy_agent",
        "orders_db":       "route_to_orders_db_agent",
        "refunds_db":      "route_to_refunds_db_agent",
    }
    return routing_map.get(intent, "route_to_product_catalog_agent") # Default to product_catalog_agent Agent

# ── Build the graph ──────────────────────────────────────────────────────────

def build_workflow() -> StateGraph:
    graph = StateGraph(SupportState)

    # Register nodes
    graph.add_node("classifier_agent",      classifier_agent)
    graph.add_node("product_catalog_agent", product_catalog_agent)
    graph.add_node("refund_policy_agent",   refund_policy_agent)
    graph.add_node("orders_db_agent",       orders_db_agent)
    graph.add_node("refunds_db_agent",      refunds_db_agent)
    graph.add_node("synthesizer_agent",     synthesizer_agent)

    # Entry point
    graph.set_entry_point("classifier_agent")

    # Router: classifier → one of four specialists  
    graph.add_conditional_edges(
        "classifier_agent",
        route_to_specialist,
        {
            "route_to_product_catalog_agent": "product_catalog_agent",
            "route_to_refund_policy_agent":   "refund_policy_agent",
            "route_to_orders_db_agent":       "orders_db_agent",
            "route_to_refunds_db_agent":      "refunds_db_agent",
        },
    )

    # All specialists → synthesizer
    graph.add_edge("product_catalog_agent", "synthesizer_agent")
    graph.add_edge("refund_policy_agent", "synthesizer_agent")
    graph.add_edge("orders_db_agent", "synthesizer_agent")
    graph.add_edge("refunds_db_agent", "synthesizer_agent")

    # Synthesizer → END
    graph.add_edge("synthesizer_agent", END)

    return graph.compile()

# ── Public API ───────────────────────────────────────────────────────────────
_workflow = None

def get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow

def run_support_query(customer_query: str) -> dict:
    """
    Entry point for the multi-agent system.

    Parameters
    ----------
    customer_query : str
        The raw natural-language query from the customer.

    Returns
    -------
    dict with keys:
        intent, routing_confidence, routing_reasoning,
        specialist_response, final_response, error (optional)
    """
    workflow = get_workflow()
    initial_state: SupportState = {
        "customer_query": customer_query,
        "intent": None,
        "routing_confidence": None,
        "routing_reasoning": None,
        "specialist_response": None,
        "final_response": None,
        "error": None,
    }
    result = workflow.invoke(initial_state)
    return result