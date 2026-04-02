# Refunds API

A FastAPI service that exposes **return request details** and **per-order return history** from a MongoDB `refunds` collection.

---

## Collection Shape

```json
{
  "return_id": "RET-3001",
  "order_id": "ORD-10002",
  "customer_name": "Sneha Patel",
  "product_name": "Sony WH-1000XM5 Headphones",
  "reason": "Defective - Left ear cup not producing sound",
  "request_date": "2026-03-10",
  "status": "pickup_scheduled",
  "pickup_date": "2026-03-15",
  "refund_method": "Original payment method (UPI)",
  "refund_amount": 24990,
  "refund_status": "pending",
  "resolution_type": "replacement",
  "replacement_order_id": "ORD-10005",
  "return_policy_days": 7,
  "eligible": true,
  "notes": null
}
```

Optional fields: `pickup_date`, `replacement_order_id`, `notes`

---

## Architecture

```
HTTP Request
     │
     ▼  app/routes/refund_routes.py
GET /api/v1/refunds/return/{return_id}   → fetch_return_details()
GET /api/v1/refunds/order/{order_id}     → fetch_returns_by_order()
     │
     ▼  app/services/refund_service.py
get_return_details()      — 404 if not found, returns full ReturnResponse
get_returns_for_order()   — 404 if no returns, returns ReturnsByOrderResponse
     │
     ▼  app/tools/refund_tools.py
Tool 1: lookup_return(return_id)
    → db.refunds.find_one({"return_id": ...}, {"_id": 0})

Tool 2: get_return_by_order(order_id)
    → db.refunds.find({"order_id": ...}, {"_id": 0}).sort("request_date", 1)
     │
     ▼  MongoDB — single `refunds` collection
```

---

## Project Structure

```
refunds_api/
├── app/
│   ├── main.py                  # FastAPI app + lifespan
│   ├── config.py                # Pydantic Settings (loads .env)
│   ├── db.py                    # Motor async connection
│   ├── routes/
│   │   └── refund_routes.py     # Endpoint definitions
│   ├── services/
│   │   └── refund_service.py    # Business logic + typed response assembly
│   ├── tools/
│   │   └── refund_tools.py      # MongoDB query wrappers (Tool 1 & 2)
│   └── schemas/
│       └── refund_schemas.py    # ReturnResponse, ReturnsByOrderResponse, ReturnSummary
├── tests/
│   ├── conftest.py              # RET-3001 and RET-3002 fixtures
│   ├── test_config.py           # Settings unit tests
│   ├── test_refund_service.py   # Service layer unit tests
│   └── test_refund_routes.py    # Endpoint integration tests
├── requirements.txt
└── .env.example
```

---

## Endpoints

### Endpoint 1 — Return Details

```
GET /api/v1/refunds/return/{return_id}
```

Calls **Tool 1** (`lookup_return`) → returns the full return document.

**Response 200**

```json
{
  "return_id": "RET-3001",
  "order_id": "ORD-10002",
  "customer_name": "Sneha Patel",
  "product_name": "Sony WH-1000XM5 Headphones",
  "reason": "Defective - Left ear cup not producing sound",
  "request_date": "2026-03-10",
  "status": "pickup_scheduled",
  "pickup_date": "2026-03-15",
  "refund_method": "Original payment method (UPI)",
  "refund_amount": 24990,
  "refund_status": "pending",
  "resolution_type": "replacement",
  "replacement_order_id": "ORD-10005",
  "return_policy_days": 7,
  "eligible": true,
  "notes": null
}
```

---

### Endpoint 2 — Returns by Order

```
GET /api/v1/refunds/order/{order_id}
```

Calls **Tool 2** (`get_return_by_order`) → returns all return requests for an order.
Each item is a `ReturnSummary` (actionable fields only — no `pickup_date`, `notes`, `replacement_order_id`).

**Response 200**

```json
{
  "order_id": "ORD-10001",
  "customer_name": "Rahul Verma",
  "total_returns": 1,
  "returns": [
    {
      "return_id": "RET-3002",
      "product_name": "MacBook Air M3 15-inch",
      "reason": "Not satisfied with performance",
      "request_date": "2026-03-14",
      "status": "evaluation",
      "resolution_type": "refund",
      "refund_amount": 134900,
      "refund_status": "pending",
      "eligible": true
    }
  ]
}
```

Both endpoints return **404** when no matching document(s) exist.

---

## Setup & Run

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
open http://localhost:8000/docs
```

## Schema Design Decisions

| Schema                   | Fields Included               | Purpose                    |
| ------------------------ | ----------------------------- | -------------------------- |
| `ReturnResponse`         | All 16 fields incl. optional  | Full detail for Endpoint 1 |
| `ReturnSummary`          | 9 actionable fields only      | List item for Endpoint 2   |
| `ReturnsByOrderResponse` | Wraps list with order + count | Envelope for Endpoint 2    |
