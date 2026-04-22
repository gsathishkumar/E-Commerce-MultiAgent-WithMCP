# E-Commerce Multi-Agent Customer Support System

A production-ready multi-agent customer support pipeline built with **LangGraph** (orchestration) and **LangChain** (agent tasks), using the **Router design pattern**. Routing is performed by an **LLM-based semantic classifier** (no keyword matching).

This service exposes a small **FastAPI** HTTP API, and internally acts as an **MCP client**: specialist agents retrieve data by calling **MCP tool servers** (Streamable HTTP transport) instead of calling bespoke REST endpoints directly.

---

## Architecture

```
Customer Query
  -> Classifier Agent (LLM intent router)
  -> Specialist Agent (calls MCP tools)
  -> Synthesizer Agent (polish + validate)
  -> Final Customer Response
```

Intents:
- `product_catalog`
- `refund_policy`
- `orders_db`
- `refunds_db`

---

## API (FastAPI)

Default base URL: `http://localhost:9000`

| Method | Path                     | Description                          |
| ------ | ------------------------ | ------------------------------------ |
| `POST` | `/api/v1/support/query`  | Run the full multi-agent pipeline    |
| `GET`  | `/health`                | Health check                         |
| `GET`  | `/settings`              | Active config (non-sensitive)        |

### `POST /api/v1/support/query`

Request:

```json
{
  "query": "Where is my order ORD-10041?"
}
```

Response:

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

Only `final_response` should be shown to end customers. The other fields are returned for observability/debugging.

### `GET /health`

```json
{ "status": "ok" }
```

`status` can be `starting` until the workflow is compiled during startup.

### `GET /settings`

```json
{
  "workflow_compiled": true,
  "model": "gpt-4o-mini",
  "mcp_servers": {
    "product_mcp_url": "http://localhost:8001/mcp",
    "refund_policy_mcp_url": "http://localhost:8002/mcp",
    "order_mcp_url": "http://localhost:8003/mcp",
    "refund_mcp_url": "http://localhost:8004/mcp"
  }
}
```

---

## MCP Tool Servers (Required)

Each specialist agent connects to an MCP server using the **Streamable HTTP** transport. You configure each server via a `*_MCP_BASE_URL`, and the application appends `/mcp`.

The following MCP tool names are called by the agents and must exist on the corresponding servers:

| Specialist Agent    | MCP Server Env Var           | Tool Name                    | Purpose                                |
| ------------------- | ---------------------------- | ---------------------------- | -------------------------------------- |
| Product Catalog RAG | `PRODUCT_MCP_BASE_URL`       | `get_product_chunks_by_query`| Top-k product catalog chunks           |
| Refund Policy RAG   | `REFUND_POLICY_MCP_BASE_URL` | `get_refund_chunks_by_query` | Top-k refund policy chunks             |
| Orders DB           | `ORDER_MCP_BASE_URL`         | `get_order_details`          | Full order document                    |
| Orders DB           | `ORDER_MCP_BASE_URL`         | `get_order_tracking_history` | Carrier metadata + tracking events     |
| Refunds DB          | `REFUND_MCP_BASE_URL`        | `get_return_details`         | Full return/refund document            |
| Refunds DB          | `REFUND_MCP_BASE_URL`        | `get_all_returns_by_order`   | All returns for an order, oldest-first |

Tool arguments used by this service:
- `get_product_chunks_by_query`: `{ "query": "<text>", "top_k": 3 }`
- `get_refund_chunks_by_query`: `{ "query": "<text>", "top_k": 4 }`
- `get_order_details`: `{ "order_id": "ORD-12345" }`
- `get_order_tracking_history`: `{ "order_id": "ORD-12345" }`
- `get_return_details`: `{ "return_id": "RET-12345" }`
- `get_all_returns_by_order`: `{ "order_id": "ORD-12345" }`

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
# OpenAI
OPENAI_API_KEY=sk-<your-OPENAI_API_KEY-here>
OPENAI_MODEL=gpt-4o-mini

# MCP Servers (the app connects to <BASE_URL>/mcp)
PRODUCT_MCP_BASE_URL=http://localhost:8001
REFUND_POLICY_MCP_BASE_URL=http://localhost:8002
ORDER_MCP_BASE_URL=http://localhost:8003
REFUND_MCP_BASE_URL=http://localhost:8004
```

### 3. Start the support API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

Alternative:

```bash
python run.py
```

---

## Usage Examples

### Product catalog query

```bash
curl -X POST http://localhost:9000/api/v1/support/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the price and warranty of the MacBook Air M3?"}'
```

### Refund policy query

```bash
curl -X POST http://localhost:9000/api/v1/support/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Can I return my phone if I have already opened the box?"}'
```

### Order status query

```bash
curl -X POST http://localhost:9000/api/v1/support/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is my order ORD-10041? Has it been dispatched?"}'
```

### Refund status query

```bash
curl -X POST http://localhost:9000/api/v1/support/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current status of my refund for return RET-5501?"}'
```

---

## Project Structure

```
ecommerce-support/
├── app/
│   ├── agents/
│   │   ├── classifier_agent.py
│   │   ├── product_catalog_agent.py
│   │   ├── refund_policy_agent.py
│   │   ├── orders_db_agent.py
│   │   ├── refunds_db_agent.py
│   │   └── synthesizer_agent.py
│   ├── api/
│   │   └── router.py
│   ├── core/
│   │   └── settings.py
│   ├── schema/
│   │   ├── query_schema.py
│   │   └── state.py
│   ├── main.py
│   └── workflow.py
├── run.py
├── .env.example
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Error Handling

Every agent and MCP tool call is wrapped in `try/except`. Failures are handled gracefully:

- Tool unavailable: the specialist agent continues with an unavailability notice; the synthesizer can add an escalation note.
- LLM call fails: the agent returns a safe fallback message and propagates an error string in `error`.
- Missing IDs: Orders/Refunds agents ask for an `ORD-...` or `RET-...` identifier before calling tools.

---

## Production Upgrade Path

| Component     | Current                         | Production Replacement                              |
| ------------- | ------------------------------- | --------------------------------------------------- |
| Retrieval     | MCP tool calls (HTTP transport) | Point `*_MCP_BASE_URL` to production MCP hosts      |
| LLM           | `OPENAI_MODEL`                  | Higher-accuracy model for harder queries            |
| State         | In-memory per request           | LangGraph checkpointing with Redis or Postgres      |
| Auth          | None                            | JWT / API key middleware on `app/main.py`           |
| Observability | Python `logging`                | LangSmith tracing or OpenTelemetry                  |
