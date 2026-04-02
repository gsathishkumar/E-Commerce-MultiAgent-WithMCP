# Orders API

A FastAPI service that exposes **order details** and **tracking history** from a MongoDB `orders` collection where tracking events are embedded as an array inside the order document.

---

## Collection Shape

```json
{
  "order_id": "ORD-10001",
  "customer_name": "Rahul Verma",
  "customer_email": "rahul.verma@wipro.com",
  "product_id": "PROD-001",
  "product_name": "MacBook Air M3 15-inch",
  "quantity": 1,
  "total_amount": 134900,
  "order_date": "2026-03-08",
  "status": "shipped",
  "tracking_id": "DELHIVERY-8834521",
  "carrier": "Delhivery",
  "estimated_delivery": "2026-03-14",
  "shipping_address": "42, Koramangala 4th Block, Bangalore 560034",
  "payment_method": "Credit Card (HDFC)",
  "tracking_updates": [
    { "date": "2026-03-08", "status": "Order placed", "location": "" },
    {
      "date": "2026-03-09",
      "status": "Packed",
      "location": "Mumbai Warehouse"
    },
    {
      "date": "2026-03-10",
      "status": "Shipped",
      "location": "Mumbai Warehouse"
    },
    { "date": "2026-03-11", "status": "In transit", "location": "Pune Hub" },
    {
      "date": "2026-03-12",
      "status": "In transit",
      "location": "Bangalore Hub"
    },
    {
      "date": "2026-03-13",
      "status": "Out for delivery",
      "location": "Koramangala"
    }
  ]
}
```

---

## Architecture

```
HTTP Request
     │
     ▼  app/routes/order_routes.py
GET /api/v1/orders/{order_id}           → fetch_order_details()
GET /api/v1/orders/{order_id}/tracking  → fetch_order_tracking()
     │
     ▼  app/services/order_service.py
get_order_details()   — validates, strips tracking_updates, returns OrderResponse
get_order_tracking()  — validates order, returns TrackingResponse
     │
     ▼  app/tools/order_tools.py
Tool 1: lookup_order(order_id)
    → db.orders.find_one({"order_id": ...}, {"_id": 0})

Tool 2: get_tracking_updates(order_id)
    → db.orders.find_one({"order_id": ...}, {"_id": 0, "tracking_updates": 1})
     │
     ▼  MongoDB — single `orders` collection
```

---

## Project Structure

```
orders_api/
├── app/
│   ├── main.py               # FastAPI app + lifespan
│   ├── config.py             # Pydantic Settings (loads .env)
│   ├── db.py                 # Motor async connection
│   ├── routes/
│   │   └── order_routes.py   # Endpoint definitions
│   ├── services/
│   │   └── order_service.py  # Business logic + typed response assembly
│   ├── tools/
│   │   └── order_tools.py    # MongoDB query wrappers
│   └── schemas/
│       └── order_schemas.py  # Pydantic models (OrderResponse, TrackingResponse)
├── tests/
│   ├── conftest.py           # Shared fixtures (real collection data)
│   ├── test_config.py        # Settings unit tests
│   ├── test_order_service.py # Service layer unit tests
│   └── test_order_routes.py  # Endpoint integration tests
├── requirements.txt
└── .env.example
```

---

## Endpoints

### Endpoint 1 — Order Details

```
GET /api/v1/orders/{order_id}
```

Calls **Tool 1** (`lookup_order`) → returns all order fields **except** `tracking_updates`.

**Response 200**

```json
{
  "order_id": "ORD-10001",
  "customer_name": "Rahul Verma",
  "customer_email": "rahul.verma@wipro.com",
  "product_id": "PROD-001",
  "product_name": "MacBook Air M3 15-inch",
  "quantity": 1,
  "total_amount": 134900,
  "order_date": "2026-03-08",
  "status": "shipped",
  "tracking_id": "DELHIVERY-8834521",
  "carrier": "Delhivery",
  "estimated_delivery": "2026-03-14",
  "shipping_address": "42, Koramangala 4th Block, Bangalore 560034",
  "payment_method": "Credit Card (HDFC)"
}
```

---

### Endpoint 2 — Tracking History

```
GET /api/v1/orders/{order_id}/tracking
```

Calls **Tool 2** (`get_tracking_updates`) → returns carrier metadata + the full `tracking_updates` array.

**Response 200**

```json
{
  "order_id": "ORD-10001",
  "tracking_id": "DELHIVERY-8834521",
  "carrier": "Delhivery",
  "estimated_delivery": "2026-03-14",
  "total_events": 6,
  "tracking_updates": [
    { "date": "2026-03-08", "status": "Order placed", "location": "" },
    {
      "date": "2026-03-09",
      "status": "Packed",
      "location": "Mumbai Warehouse"
    },
    {
      "date": "2026-03-10",
      "status": "Shipped",
      "location": "Mumbai Warehouse"
    },
    { "date": "2026-03-11", "status": "In transit", "location": "Pune Hub" },
    {
      "date": "2026-03-12",
      "status": "In transit",
      "location": "Bangalore Hub"
    },
    {
      "date": "2026-03-13",
      "status": "Out for delivery",
      "location": "Koramangala"
    }
  ]
}
```

Both endpoints return **404** when the `order_id` does not exist.

---

## Setup & Run

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
open http://localhost:8000/docs
```
