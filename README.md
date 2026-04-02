# ecommerce-support (orchestrator)

FastAPI app with a LangGraph workflow: an LLM classifier routes each customer query to one of four agents (product catalog RAG, refund policy RAG, orders DB, refunds DB). Each agent calls its dedicated backend, and a synthesizer rewrites the final response. Exposes /support/query and /health on port 9000; returns both routing metadata and polished text.

# product-rag-api

RAG service for product knowledge. Ingests pdf files chunks + embeds them into Postgres/pgvector, and serves semantic search (/api/v1/retrieve). Also provides ingestion and file-status endpoints. Intended to supply grounded product snippets to the product-catalog agent.

# refund-rag-api

Same RAG pipeline as above but for refund/returns policy documents. Provides the policy search endpoint used by the refund-policy agent, plus ingestion and status endpoints.

# order-api

FastAPI + MongoDB service exposing two endpoints: order details (/api/v1/orders/{order_id}) and tracking history (/api/v1/orders/{order_id}/tracking). Stores full order docs with embedded tracking updates; used by the orders DB agent.

# refund-api

FastAPI + MongoDB service for return/refund records. Two endpoints: full return by return_id and all returns for an order_id. Supplies data to the refunds DB agent.

# Big picture

The main support app is a router-plus-synthesizer layer; the four backend services supply trustworthy data: two RAG searchers for static knowledge (products, policy) and two CRUD-style APIs for live records (orders, returns).
