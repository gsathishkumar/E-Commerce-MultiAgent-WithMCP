# Refunds API (FastAPI + MCP)

This service exposes return/refund details and per-order return history from MongoDB.

It supports two interfaces:
- REST API under `/refund-api/api/v1`
- MCP server (Streamable HTTP) under `/mcp`, exposing the same operations as tools

Default ports:
- Local dev (via `python run.py`): `8004`
- Docker container (see `Dockerfile`): listens on `8000` (map host port as needed)

---

## REST API

Base URL (local dev): `http://localhost:8004/refund-api/api/v1`

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/refunds/return/{return_id}` | Return details |
| `GET` | `/refunds/order/{order_id}` | Returns by order |

Health and config:
- `GET http://localhost:8004/health`
- `GET http://localhost:8004/settings`

API docs:
- REST: `http://localhost:8004/docs`

---

## MCP Server

This service exposes an MCP server using `fastapi-mcp`:

- MCP endpoint (Streamable HTTP): `http://localhost:8004/mcp`
- Exposed tool names:
  - `get_return_details`
  - `get_all_returns_by_order`

Tool arguments:
- `get_return_details`: `{ "return_id": "RET-12345" }`
- `get_all_returns_by_order`: `{ "order_id": "ORD-12345" }`

The MCP tools map to the REST routes:
- `get_return_details` -> `GET /refund-api/api/v1/refunds/return/{return_id}`
- `get_all_returns_by_order` -> `GET /refund-api/api/v1/refunds/order/{order_id}`

---

## Setup & Run (Local)

```bash
pip install -r requirements.txt
cp .env.example .env
python run.py
```

---

## Docker (Optional)

Build and run (container listens on `8000`):

```bash
docker build -t ecommerce/refund-api:latest .
docker run --rm -p 8004:8000 --env-file .env ecommerce/refund-api:latest
```
