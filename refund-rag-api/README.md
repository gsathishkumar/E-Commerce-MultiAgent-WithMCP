# RAG Ingestion API

A production-ready FastAPI service for document ingestion, background processing, and semantic retrieval (RAG) — backed by **PostgreSQL + pgvector**.

---

## Stack

| Layer           | Technology                                                |
| --------------- | --------------------------------------------------------- |
| API framework   | FastAPI (async)                                           |
| Metadata DB     | PostgreSQL 16 via `asyncpg` + SQLAlchemy async ORM        |
| Vector store    | PostgreSQL `pgvector` extension (`document_chunks` table) |
| Vector index    | HNSW (`vector_cosine_ops`) — configurable to IVFFlat      |
| Embeddings      | OpenAI - Model `text-embedding-3-small`)                  |
| Text chunking   | LangChain `RecursiveCharacterTextSplitter`                |
| Background work | `ThreadPoolExecutor` (stored in `app.state`)              |

---

## Project Structure

```
rag_api/
├── app/
│   ├── main.py                  # FastAPI app + lifespan
│   ├── core/
│   │   └── config.py            # Pydantic settings (postgres, embedding, chunking)
│   ├── db/
│   │   └── session.py           # Async engine, CREATE EXTENSION vector, init_db()
│   ├── models/
│   │   ├── file_record.py       # SQLAlchemy: files table + FileStatus enum
│   │   └── document_chunk.py    # SQLAlchemy: document_chunks table (Vector column)
│   ├── schemas/
│   │   └── file_schema.py       # Pydantic request/response models
│   ├── services/
│   │   ├── file_parser.py       # Text extraction (txt/pdf/docx/md)
│   │   ├── file_processor.py    # Background worker (chunk → embed → pgvector)
│   │   └── vector_store.py      # PgVectorStore: add_chunks / search / remove_file
│   └── api/
│       ├── __init__.py          # Router aggregator
│       └── routes/
│           ├── ingestion.py     # POST /api/v1/ingest
│           ├── files.py         # GET  /api/v1/files  &  /api/v1/files/status
│           └── retrieval.py     # GET  /api/v1/retrieve
├── uploads/                     # Uploaded files (one sub-dir per file_id)
├── Dockerfile
├── run.py
├── requirements.txt
└── .env
```

---

## Quickstart

### Option A — Docker Compose (recommended)

```bash
docker build -t ecommerce/refund_rag_api:latest .
docker compose up
```

Spins up:

- `refund_rag_api` — FastAPI app on port 8002

API docs: **http://localhost:8002/docs**

### Option B — Local

```bash
# 1. Start Postgres with pgvector (Docker is easiest)
docker run -d --name pgvector \
  -e POSTGRES_DB=ragdb -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 pgvector/pgvector:pg16

# 2. Create virtualenv & install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure
.env   # edit if needed

# 4. Run
python run.py
```

---

## API Endpoints

### `POST /api/v1/ingest`

Upload a document for ingestion.

**Accepted types:** `.txt`, `.pdf`, `.docx`, `.md`  
**Max size:** 1 MB

**Validations:**

- `413` — file exceeds 1 MB
- `415` — unsupported file type
- `409` — duplicate content (SHA-256 match)
- `400` — empty file

**Response `202`:**

```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "report.pdf",
  "file_size": 45678,
  "status": "pending",
  "message": "File accepted and queued for processing.",
  "created_at": "2024-01-15T10:30:00"
}
```

---

### `GET /api/v1/files`

List all uploaded files with their processing status.

---

### `GET /api/v1/files/status?file_id=<id>`

Get status for a specific file.

**Statuses:** `pending` → `processing` → `completed` / `failed`

---

### `GET /api/v1/retrieve?query=<text>&top_k=5`

Semantic search over all ingested chunks.

**Response:**

```json
{
  "query": "What are the revenue figures?",
  "results": [
    {
      "file_id": "550e8400-...",
      "original_filename": "report.pdf",
      "chunk_index": 7,
      "text": "Revenue for Q3 was $4.2M...",
      "score": 0.91
    }
  ]
}
```

---

## Database Schema

### `files` table (SQLite metadata)

| Column                  | Type           | Notes                               |
| ----------------------- | -------------- | ----------------------------------- |
| id                      | VARCHAR PK     | UUID                                |
| original_filename       | VARCHAR        |                                     |
| file_path               | VARCHAR        | disk location                       |
| file_size               | INTEGER        | bytes                               |
| content_hash            | VARCHAR UNIQUE | SHA-256 for dedup                   |
| mime_type               | VARCHAR        |                                     |
| status                  | ENUM           | pending/processing/completed/failed |
| chunk_count             | INTEGER        | set after processing                |
| error_message           | TEXT           | set on failure                      |
| created_at / updated_at | TIMESTAMP      |                                     |

### `document_chunks` table (pgvector)

| Column            | Type                  | Notes                |
| ----------------- | --------------------- | -------------------- |
| id                | SERIAL PK             |                      |
| file_id           | VARCHAR FK → files.id | CASCADE DELETE       |
| original_filename | VARCHAR               |                      |
| chunk_index       | INTEGER               | position within file |
| text              | TEXT                  | raw chunk content    |
| embedding         | VECTOR(384)           | pgvector column      |
| created_at        | TIMESTAMP             |                      |

**Index:** `HNSW` on `embedding` using `vector_cosine_ops`

---

## Architecture: Lifespan & Background Processing

```python
@asynccontextmanager
async def lifespan(app):
    await init_db()                    # CREATE EXTENSION vector + CREATE TABLE
    await vector_store.create_index()  # CREATE INDEX IF NOT EXISTS (HNSW)
    executor = ThreadPoolExecutor(max_workers=4)
    app.state.executor = executor      # shared across all requests
    vector_store.load_model("all-MiniLM-L6-v2")
    yield
    executor.shutdown(wait=True)
```

```
POST /ingest
    │
    ├─ validate (size / type / duplicate)
    ├─ save file to disk
    ├─ INSERT files row (status=PENDING)
    └─ loop.run_in_executor(app.state.executor, lambda: asyncio.run(process_file_async(...)))
                                │
                                ▼  (ThreadPoolExecutor worker thread)
                        UPDATE files SET status=PROCESSING
                        extract_text()          → raw string
                        RecursiveCharacterTextSplitter → chunks[]
                        SentenceTransformer.encode() → embeddings[]
                        INSERT INTO document_chunks (bulk)
                        UPDATE files SET status=COMPLETED, chunk_count=N
```
