# Orders API (FastAPI + MCP)

This service exposes order details and tracking history from MongoDB.

It supports two interfaces:
- REST API under `/order-api/api/v1`
- MCP server (Streamable HTTP) under `/mcp`, exposing the same operations as tools

Default ports:
- Local dev (via `python run.py`): `8003`
- Docker container (see `Dockerfile`): listens on `8000` (map host port as needed)

---

## REST API

Base URL (local dev): `http://localhost:8003/order-api/api/v1`

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/orders/{order_id}` | Order details |
| `GET` | `/orders/{order_id}/tracking` | Tracking history |

Health and config:
- `GET http://localhost:8003/health`
- `GET http://localhost:8003/settings`

API docs:
- REST: `http://localhost:8003/docs`

---

## MCP Server

This service exposes an MCP server using `fastapi-mcp`:

- MCP endpoint (Streamable HTTP): `http://localhost:8003/mcp`
- Exposed tool names:
  - `get_order_details`
  - `get_order_tracking_history`

Tool arguments:
- `get_order_details`: `{ "order_id": "ORD-12345" }`
- `get_order_tracking_history`: `{ "order_id": "ORD-12345" }`

The MCP tools map to the REST routes:
- `get_order_details` -> `GET /order-api/api/v1/orders/{order_id}`
- `get_order_tracking_history` -> `GET /order-api/api/v1/orders/{order_id}/tracking`

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
docker build -t ecommerce/order-api:latest .
docker run --rm -p 8003:8000 --env-file .env ecommerce/order-api:latest
```
