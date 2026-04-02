# E-Commerce Multi-Agent Customer Support System

A production-ready multi-agent customer support pipeline built with **LangGraph** (orchestration) and **LangChain** (agent tasks), using the **Router design pattern**. Routing is performed by an **LLM-based semantic classifier** — no keyword matching. All specialist tool endpoints are consumed from external FastAPI services running in **Docker Desktop**.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Customer Query                            │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
                  ┌─────────────────────────┐
                  │     Classifier Agent    │
                  │  OpenAI Model· temp=0   │
                  │  Semantic intent router │
                  └──────────┬──────────────┘
                             │
           intent ∈ { product_catalog | refund_policy | orders_db | refunds_db }
                             │
         ┌───────────────────┼─────────┬───────────────┐
         │           ┌───────┘         |               |
         ▼           ▼                 ▼               ▼
 ┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────┐
 │   Product    │ │    Refund    │ │ Orders   │ │  Refunds DB  │
 │  Catalog     │ │   Policy     │ │   DB     │ │    Agent     │
 │  RAG Agent   │ │  RAG Agent   │ │  Agent   │ │              │
 │  1 tool      │ │  1 tool      │ │  2 tools │ │  2 tools     │
 └──────┬───────┘ └──────┬───────┘ └────┬─────┘ └──────┬───────┘
        │                │              │               │
        └────────────────┴──────────────┴───────────────┘
                                │
                                ▼
                  ┌─────────────────────────┐
                  │    Synthesizer Agent    │
                  │   (Polish & Validate)   │
                  └──────────┬──────────────┘
                             │
                             ▼
                    Final Customer Response
```

---

## Agents

### Classifier Agent (`agents/classifier_agent.py`)

The entry node and semantic router. Sends the raw customer query to `OpenAI Model` with a strict system prompt that defines all four intents. Returns a structured JSON payload — `intent`, `confidence` (0–1), and `reasoning` — which LangGraph uses to select the next node via `add_conditional_edges`. Temperature is fixed at `0` for deterministic, consistent routing.

### Product Catalog RAG Agent (`agents/product_catalog_agent.py`)

Handles queries about products not yet purchased. Calls the Product RAG endpoint to retrieve the most relevant catalog chunks, injects them into a context-augmented prompt, and passes the result to `OpenAI Model` to produce a grounded answer. The LLM is instructed never to invent product details beyond what the retrieved context contains.

**Tool:** `GET http://localhost:8001/product-rag/api/v1/retrieve`
Query params : ?query=customer_query&top_k=3

### Refund Policy RAG Agent (`agents/refund_policy_agent.py`)

Handles all questions about return, refund, and exchange policies. Same RAG pattern as the Product Catalog agent — retrieves top-k policy chunks and augments the prompt before generation. `top_k` is set to `4` to capture multi-section policy answers (e.g. a query that touches both eligibility and timelines).

**Tool:** `GET http://localhost:8002/refund-rag/api/v1/retrieve`
Query params : ?query=customer_query&top_k=4

### Orders DB Agent (`agents/orders_db_agent.py`)

Handles queries about a specific placed order. Extracts the `ORD-XXXXX` identifier from the query using a regex, then calls both tools in sequence and merges the responses into a single JSON context for `OpenAI Model`. If no order ID is found in the query, the agent asks the customer to provide one before any tool call is made.

**Tool 1:** `GET http://localhost:8003/order-api/api/v1/orders/{order_id}`
Returns the full order document from MongoDB.

**Tool 2:** `GET http://localhost:8003/order-api/api/v1/orders/{order_id}/tracking`
Returns carrier metadata and tracking events in chronological order.

### Refunds DB Agent (`agents/refunds_db_agent.py`)

Handles queries about an existing return or refund request. Extracts a `RET-XXXXX` return ID (priority) and/or `ORD-XXXXX` order ID from the query. If a return ID is present, Tool 1 is called. If an order ID is present, Tool 2 is called. Both can be called in the same turn if both IDs appear in the query. The combined data is passed to `OpenAI Model` for a grounded response.

**Tool 1:** `GET http://localhost:8004/refund-api/api/v1/refunds/return/{return_id}`
Returns the full return/refund document for a specific return.

**Tool 2:** `GET http://localhost:8004/refund-api/api/v1/refunds/order/{order_id}`
Returns all return requests for an order, sorted oldest-first.

### Synthesizer Agent (`agents/synthesizer_agent.py`)

The final node that every specialist route passes through before returning to the caller. Rewrites the specialist's raw output to be warm, professional, and free of internal jargon or system field names. Also validates relevance — if the specialist response is incomplete or off-topic relative to the original query, it adds an escalation note directing the customer to contact support. Temperature is set to `0` to stop creativity.

---

## Shared State (`agents/state.py`)

All nodes read from and write to a single `TypedDict` that flows through the LangGraph graph:

```python
class SupportState(TypedDict):
    customer_query: str                    # Original customer input (immutable)
    intent: Optional[str]                  # product_catalog | refund_policy | orders_db | refunds_db
    routing_confidence: Optional[float]    # 0.0–1.0
    routing_reasoning: Optional[str]       # One-sentence explanation from the LLM
    specialist_response: Optional[str]     # Raw output from the matched specialist agent
    final_response: Optional[str]          # Polished output from the synthesizer
    error: Optional[str]                   # Propagated error message if any step fails
```

---

## Workflow (`workflow.py`)

The LangGraph graph is built by `build_workflow()` and compiled once at startup. The graph wiring:

```
classifier_agent
    └── add_conditional_edges(route_to_specialist)
            ├── product_catalog  →  product_catalog_agent
            ├── refund_policy    →  refund_policy_agent
            ├── orders_db        →  orders_db_agent
            └── refunds_db       →  refunds_db_agent

product_catalog_agent  ──┐
refund_policy_agent    ──┤──► synthesizer_agent ──► END
orders_db_agent        ──┤
refunds_db_agent       ──┘
```

`route_to_specialist()` is a pure Python function that reads `state["intent"]` — already set by the LLM — and maps it to the appropriate node name. No routing logic lives here; all intelligence lives in the classifier.

---

## Application Server (`main.py`)

FastAPI application running on **port 9000**. The LangGraph workflow is compiled exactly once during startup using the FastAPI `lifespan` context manager and stored on `app.state.workflow`. All requests share the compiled graph with no per-request compilation overhead.

### Endpoints

| Method | Path             | Description                                       |
| ------ | ---------------- | ------------------------------------------------- |
| `POST` | `/support/query` | Run the full multi-agent pipeline                 |
| `GET`  | `/health`        | Health check + workflow status + active tool URLs |

### `POST /support/query`

**Request:**

```json
{
  "query": "Where is my order ORD-10041?"
}
```

**Response:**

```json
{
  "query": "Where is my order ORD-10041?",
  "intent": "orders_db",
  "routing_confidence": 0.98,
  "routing_reasoning": "The query asks for the status of a specific placed order by ID.",
  "specialist_response": "Raw specialist agent output...",
  "final_response": "Polished customer-facing response...",
  "error": null
}
```

All intermediate fields (`intent`, `routing_confidence`, `routing_reasoning`, `specialist_response`) are returned for observability and debugging. Only `final_response` should be shown to the end customer.

### `GET /support/health`

```json
{
  "status": "ok",
  "workflow_compiled": true,
  "model": "OpenAI Model",
  "tool_endpoints": {
    "product_rag": "http://localhost:8001/product-rag/api/v1/retrieve",
    "refund_policy_rag": "http://localhost:8002/refund-rag/api/v1/retrieve",
    "order_base": "http://localhost:8003/order-api/api/v1/orders",
    "refund_base": "http://localhost:8004/refund-api/api/v1/refunds"
  }
}
```

---

## Project Structure

```
ecommerce-support/
├── app/
│   ├── agents/
│   │   ├── classifier_agent.py        # LLM-based semantic router (OpenAI Model, temp=0)
│   │   ├── product_catalog_agent.py   # RAG agent — Product catalog (1 tool)
│   │   ├── refund_policy_agent.py     # RAG agent — Return/refund policy (1 tool)
│   │   ├── orders_db_agent.py         # DB agent — Order doc + tracking (2 tools)
│   │   ├── refunds_db_agent.py        # DB agent — Return doc + returns by order (2 tools)
│   │   └── synthesizer_agent.py       # Final polish, validation, escalation
│   ├── api/
│   │   └── router.py                  # FastAPI routes (/support/query, /health)
│   ├── schema/
│   │   ├── query_schema.py            # Request/response models
│   │   └── state.py                   # Shared LangGraph TypedDict state
│   ├── main.py                        # FastAPI app with lifespan startup, port 9000
│   ├── settings.py                    # Pydantic settings + tool endpoints
│   └── workflow.py                    # LangGraph graph definition — build_workflow()
├── run.py                             # Entrypoint wrapper for local runs
├── .env                               # Environment variables (example copied here)
├── .dockerignore
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required
OPENAI_API_KEY=sk-...

# Tool endpoints (Docker Desktop) — defaults shown, override if your ports differ
PRODUCT_RAG_BASE_URL=http://localhost:8001
REFUND_POLICY_RAG_BASE_URL=http://localhost:8002
ORDER_API_BASE_URL=http://localhost:8003
REFUND_API_BASE_URL=http://localhost:8004
```

### 3. Verify Docker tool services are running

```bash
# Product RAG
curl -X POST http://localhost:8001/product-rag/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 1}'

# Refund Policy RAG
curl -X POST http://localhost:8002/refund-rag/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 1}'

# Orders DB
curl http://localhost:8003/order-api/api/v1/orders/ORD-001
curl http://localhost:8003/order-api/api/v1/orders/ORD-001/tracking

# Refunds DB
curl http://localhost:8004/refund-api/api/v1/refunds/order/ORD-001
curl http://localhost:8004/refund-api/api/v1/refunds/return/RET-001
```

### 4. Start the support API

```bash
uvicorn main:app --host 0.0.0.0 --port 9000 --reload
```

Expected startup output:

```
INFO:     Compiling LangGraph workflow ...
INFO:     LangGraph workflow compiled and ready.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9000
```

---

## Usage Examples

### Product catalog query

```bash
curl -X POST http://localhost:9000/support/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the price and warranty of the MacBook Air M3?"}'
```

### Refund policy query

```bash
curl -X POST http://localhost:9000/support/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Can I return my phone if I have already opened the box?"}'
```

### Order status query

```bash
curl -X POST http://localhost:9000/support/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is my order ORD-10041? Has it been dispatched?"}'
```

### Refund status query

```bash
curl -X POST http://localhost:9000/support/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current status of my refund for return RET-5501?"}'
```

---

## Sample Queries by Agent

| Agent               | Sample Query                                                                   |
| ------------------- | ------------------------------------------------------------------------------ |
| Product Catalog RAG | `"What is the stock availability and rating of the Sony WH-1000XM5?"`          |
| Product Catalog RAG | `"Does the Samsung 65-inch QLED TV include installation? What are the specs?"` |
| Refund Policy RAG   | `"What is the return window for electronics?"`                                 |
| Refund Policy RAG   | `"How long does a refund take after the pickup is completed?"`                 |
| Orders DB           | `"Show me the full details and payment status of order ORD-10023."`            |
| Orders DB           | `"What is the tracking status of ORD-10041? When will it arrive?"`             |
| Refunds DB          | `"What is the current status of my refund for RET-5501?"`                      |
| Refunds DB          | `"Show me all return requests linked to order ORD-10041."`                     |

---

## Tool Endpoint Reference

| Agent               | Method | Endpoint                                             | Purpose                                |
| ------------------- | ------ | ---------------------------------------------------- | -------------------------------------- |
| Product Catalog RAG | `POST` | `:8001/product-rag/api/v1/retrieve`                  | Top-k product catalog chunks           |
| Refund Policy RAG   | `POST` | `:8002/refund-rag/api/v1/retrieve`                   | Top-k refund policy chunks             |
| Orders DB           | `GET`  | `:8003/order-api/api/v1/orders/{order_id}`           | Full order document from MongoDB       |
| Orders DB           | `GET`  | `:8003/order-api/api/v1/orders/{order_id}/tracking`  | Carrier metadata + tracking events     |
| Refunds DB          | `GET`  | `:8004/refund-api/api/v1/refunds/return/{return_id}` | Full return/refund document            |
| Refunds DB          | `GET`  | `:8004/refund-api/api/v1/refunds/order/{order_id}`   | All returns for an order, oldest-first |

---

## Error Handling

Every agent and tool call is wrapped in `try/except`. Failures are handled gracefully at each layer:

- **Tool unavailable** — the agent injects an unavailability notice into the prompt context and continues to the LLM step; the synthesizer appends an escalation note.
- **LLM call fails** — the agent returns a safe fallback message and propagates the error string in `state["error"]`.
- **Classifier fails** — falls back to `product_catalog` intent so every request always completes.
- **Missing IDs** — the Orders DB and Refunds DB agents detect a missing `ORD-` or `RET-` identifier and return a polite clarification prompt without making any tool calls.
- **Workflow exception** — `main.py` catches unhandled exceptions and returns HTTP `500` with the error detail.

---

## Production Upgrade Path

| Component     | Current                  | Production Replacement                                 |
| ------------- | ------------------------ | ------------------------------------------------------ |
| RAG retrieval | HTTP call to Docker tool | Same pattern — replace Docker URL with production host |
| LLM           | `OpenAI Model`           | `gpt-4o` for higher accuracy on complex queries        |
| Classifier    | Zero-shot single turn    | Add few-shot examples for edge-case disambiguation     |
| State         | In-memory per request    | LangGraph checkpointing with Redis or Postgres         |
| ID extraction | Regex                    | Named entity recognition or LLM-assisted extraction    |
| Auth          | None                     | JWT / API key middleware on `main.py`                  |
| Observability | Python `logging`         | LangSmith tracing or OpenTelemetry                     |

---

## Key Design Decisions

**Router pattern over parallel fan-out** — a single classifier node with conditional edges keeps routing logic fully separated from business logic. Adding a fifth agent requires one new node, one new edge, and one new intent label in the classifier prompt — nothing else changes.

**LLM-based routing** — `OpenAI Model` at temperature `0` handles paraphrasing, typos, multilingual input, and ambiguous phrasing that regex or keyword matching would miss.

**RAG flow order** — tool retrieval always happens before the LLM generation call. This ensures the model generates from grounded context rather than hallucinating and attempting to verify afterward.

**Lifespan for workflow compilation** — `build_workflow()` is called once at application startup via the FastAPI `lifespan` context manager. The compiled graph is stored on `app.state.workflow` and shared across all requests — the idiomatic FastAPI pattern for shared resources.

**Synthesizer as a universal quality gate** — rather than embedding tone and style rules in each specialist's prompt, a single synthesizer node owns all customer-facing formatting. Tone policy changes in exactly one place.
