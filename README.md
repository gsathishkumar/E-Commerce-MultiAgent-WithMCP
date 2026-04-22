# E-Commerce Multi-Agent With MCP

This repository contains a customer-support **orchestrator** plus four backend services. The orchestrator routes customer questions to specialist agents (RAG + DB) and calls the backends via **MCP**.

The backend services expose **FastAPI REST** endpoints, but they also expose the same capabilities as **MCP tool servers** (Streamable HTTP at `/mcp`). The orchestrator (`ecommerce-support`) is an **MCP client** and uses tool calls.

---

## Services

| Folder               | Purpose                              | port   | REST base path        | MCP endpoint | MCP tools used by orchestrator                    |
| -------------------- | ------------------------------------ | ------ | --------------------- | ------------ | ------------------------------------------------- |
| `ecommerce-support/` | LangGraph router + synthesizer API   | `9000` | `/api/v1/support`     | (client)     | Calls all tools below                             |
| `product-rag-api/`   | Product knowledge RAG (pgvector)     | `8001` | `/product-rag/api/v1` | `/mcp`       | `get_product_chunks_by_query`                     |
| `refund-rag-api/`    | Refund/returns policy RAG (pgvector) | `8002` | `/refund-rag/api/v1`  | `/mcp`       | `get_refund_chunks_by_query`                      |
| `order-api/`         | Orders DB (MongoDB)                  | `8003` | `/order-api/api/v1`   | `/mcp`       | `get_order_details`, `get_order_tracking_history` |
| `refund-api/`        | Refunds/returns DB (MongoDB)         | `8004` | `/refund-api/api/v1`  | `/mcp`       | `get_return_details`, `get_all_returns_by_order`  |

---

## Orchestrator API (`ecommerce-support`)

Base URL: `http://localhost:9000`

- `POST /api/v1/support/query` — run the multi-agent pipeline
- `GET /health` — liveness (`status` can be `starting` during startup)
- `GET /settings` — shows configured MCP server URLs (non-sensitive)

Example:

```bash
curl -X POST http://localhost:9000/api/v1/support/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Where is my order ORD-10041?"}'
```

---

## MCP Endpoints (backend services)

Each backend mounts an MCP server at:

- `http://localhost:8001/mcp`
- `http://localhost:8002/mcp`
- `http://localhost:8003/mcp`
- `http://localhost:8004/mcp`

The orchestrator connects using base URLs like `http://localhost:8001` and appends `/mcp` internally.

---

## Quickstart (Local Dev)

### 1) Start databases

RAG services require Postgres + pgvector (example):

```bash
docker run -d --name pgvector \
  -e POSTGRES_DB=ragdb -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 pgvector/pgvector:pg16
```

Orders/Refunds services require MongoDB (example):

```bash
docker run -d --name mongo \
  -p 27017:27017 \
  mongo:7
```

### 2) Run backend services (tool servers)

In four separate terminals:

```bash
cd product-rag-api && pip install -r requirements.txt && cp .env.example .env && python run.py
cd refund-rag-api  && pip install -r requirements.txt && cp .env.example .env && python run.py
cd order-api       && pip install -r requirements.txt && cp .env.example .env && python run.py
cd refund-api      && pip install -r requirements.txt && cp .env.example .env && python run.py
```

### 3) Run the orchestrator

```bash
cd ecommerce-support
pip install -r requirements.txt
cp .env.example .env
python run.py
```

---

## Notes

- The RAG services expose many REST endpoints (ingest, file status, retrieve), but only the **retrieval** operation is exposed as an MCP tool (via `operation_id`).
- If you change ports, update the orchestrator env vars in `ecommerce-support/.env`:
  - `PRODUCT_MCP_BASE_URL`, `REFUND_POLICY_MCP_BASE_URL`, `ORDER_MCP_BASE_URL`, `REFUND_MCP_BASE_URL`

See each service folder README for service-specific configuration.
