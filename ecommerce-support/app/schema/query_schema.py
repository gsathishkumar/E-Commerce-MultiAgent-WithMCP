from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    query: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"query": "Where is my order ORD-10041?"},
                {"query": "Can I return an opened laptop?"},
                {"query": "What is the price of the MacBook Air M3?"},
                {"query": "Status of my refund for RET-5501"},
            ]
        }
    }

class QueryResponse(BaseModel):
    query: str
    intent: Optional[str] = None
    routing_confidence: Optional[float] = None
    routing_reasoning: Optional[str] = None
    specialist_response: Optional[str] = None
    final_response: Optional[str] = None
    error: Optional[str] = None