# Product RAG API (FastAPI + MCP)

This service provides:
- A REST API for document ingestion and retrieval under `/product-rag/api/v1`.
- An MCP server (Streamable HTTP) under `/mcp` exposing retrieval as a tool.

Default ports:
- Local dev (via `python run.py`): `8001`
- Docker container (see `Dockerfile`): listens on `8000` (map host port as needed)

---

## REST API

Base URL (local dev): `http://localhost:8001/product-rag/api/v1`

| Method | Path | Description |
| ------ | ---- | ----------- |
| `POST` | `/ingest` | Upload and ingest a PDF document |
| `GET`  | `/files` | List uploaded files + processing status |
| `GET`  | `/files/status?file_id=<id>` | Get status for a specific file |
| `GET`  | `/retrieve?query=<text>&top_k=<int>` | Retrieve semantically relevant chunks |

Notes:
- Accepted upload types: `.pdf`
- Max file size: 1 MB (configurable)

Health and config:
- `GET http://localhost:8001/health`
- `GET http://localhost:8001/settings`

---

## MCP Server

This service also exposes an MCP server using `fastapi-mcp`.

- MCP endpoint (Streamable HTTP): `http://localhost:8001/mcp`
- Exposed tool name: `get_product_chunks_by_query`

Tool arguments:
- `query` (string, required)
- `top_k` (int, optional; defaults to server config)

The MCP tool maps to the same logic as the REST retrieval endpoint (`GET /product-rag/api/v1/retrieve`).

---

## Setup (Local)

1) Install dependencies

```bash
pip install -r requirements.txt
```

2) Configure environment

```bash
cp .env.example .env
```

3) Start Postgres with pgvector (example)

```bash
docker run -d --name pgvector \
  -e POSTGRES_DB=ragdb -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 pgvector/pgvector:pg16
```

4) Run

```bash
python run.py
```

API docs:
- REST: `http://localhost:8001/docs`

---

## Docker (Optional)

Build and run (container listens on `8000`):

```bash
docker build -t ecommerce/product-rag-api:latest .
docker run --rm -p 8001:8000 --env-file .env ecommerce/product-rag-api:latest
```
