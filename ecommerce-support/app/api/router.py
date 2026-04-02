import logging
from fastapi import APIRouter, HTTPException, Request
from app.schema.query_schema import QueryRequest, QueryResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["Support"])

@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Submit a customer support query",
    description=(
        "Runs the full multi-agent pipeline:\n"
        "1. **Classifier** — semantically routes the query to the correct specialist.\n"
        "2. **Specialist agents** — calls the appropriate Docker tool endpoint(s).\n"
        "3. **Synthesizer** — polishes and validates the response.\n\n"
        "Returns all intermediate fields for observability."
    ),
)
def handle_query(request: Request, query_request: QueryRequest) -> QueryResponse:
    workflow = request.app.state.workflow

    initial_state = {
        "customer_query": query_request.query,
        "intent": None,
        "routing_confidence": None,
        "routing_reasoning": None,
        "specialist_response": None,
        "final_response": None,
        "error": None,
    }

    try:
        result = workflow.invoke(initial_state)
        # result = initial_state
    except Exception as exc:
        logger.exception("Workflow invocation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return QueryResponse(
        query=query_request.query,
        intent=result.get("intent"),
        routing_confidence=result.get("routing_confidence"),
        routing_reasoning=result.get("routing_reasoning"),
        specialist_response=result.get("specialist_response"),
        final_response=result.get("final_response"),
        error=result.get("error"),
    )



