*** Begin Project Overview ***

# Distributed E-Commerce Order Engine

Production-minded prototype of a distributed e-commerce order engine with both a CLI and a FastAPI backend. The project demonstrates inventory management, reservation logic, order placement, payment simulation, audit logging, simple fraud detection, and failure injection — all implemented using in-memory stores and clean modular design.

## Project layout (important files)

- `app/main.py` — FastAPI application factory and root status endpoint.
- `app/api/` — API routers: `products.py`, `carts.py`, `orders.py`, `misc.py`.
- `app/services/` — core services: `product_service.py`, `cart_service.py`, `order_service.py`, `payment_service.py`, `fraud_service.py`.
- `app/schemas/` — Pydantic schemas for requests/responses.
- `app/utils/` — `event_bus.py`, `audit_logger.py`.
- `run_features_test.py` — full feature test harness (CLI & API flows).
- `test_api_extended.py` — API-level integration tests using FastAPI TestClient.

## Quick start (local development)

1. Create & activate a virtual environment (Windows PowerShell example):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run feature tests (recommended):

```powershell
python run_features_test.py
python test_api_extended.py
```

4. Start the API (development):

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger UI: http://127.0.0.1:8000/docs

## Core API endpoints (examples)

- Products
  - `POST /api/v1/products`  — create product (name, price, quantity)
  - `GET  /api/v1/products`  — list products
  - `PUT  /api/v1/products/{id}` — update product

- Cart
  - `POST   /api/v1/carts/{user_id}/items`  — add item `{product_id, quantity}`
  - `PUT    /api/v1/carts/{user_id}/items`  — update item
  - `DELETE /api/v1/carts/{user_id}/items/{product_id}` — remove item
  - `GET    /api/v1/carts/{user_id}` — view cart

- Orders
  - `POST /api/v1/orders/place` — place order from cart (user_id, coupon, idempotency_key)
  - `GET  /api/v1/orders` — list orders
  - `POST /api/v1/orders/{order_id}/cancel` — cancel order
  - `POST /api/v1/orders/{order_id}/return` — return product

- Misc
  - `GET  /api/v1/logs` — view audit logs
  - `GET  /api/v1/inventory/low-stock?threshold=5` — low-stock report
  - `POST /api/v1/simulate/failure?enable=true` — toggle payment failure injection
  - `GET  /api/v1/fraud/flags` — view fraud flags

## CLI

The project includes CLI helpers (menu-driven) for local testing and simulation. Run the CLI entrypoint (if present) or use the test harness scripts for automated behavior.

## Testing

- `run_features_test.py` runs a full end-to-end feature validation including reservation expiry, concurrency scenarios, payments (including injected failures), discounts, cancel/return, and idempotency.
- `test_api_extended.py` exercises the HTTP API using FastAPI TestClient.

## Notes & next steps

- This is an in-memory prototype. For production you should:
  - Replace in-memory stores with a durable DB and use transactions.
  - Convert services to `async` and use proper concurrency primitives.
  - Add authentication, rate limiting, monitoring, and persistent audit logs.

## Publishing to GitHub

1. Add a `.gitignore` (exclude `.venv/`, `__pycache__`, `.env`, etc.).
2. Verify tests pass locally.
3. Initialize git, create a repo on GitHub, and push:

```powershell
git init
git add .
git commit -m "Initial import: Distributed E-Commerce Order Engine"
# create remote and push (use gh CLI or GitHub web)
git remote add origin https://github.com/USERNAME/REPO.git
git branch -M main
git push -u origin main
```

If you want, I can prepare a final cleanup (remove legacy/duplicate top-level folders and `__pycache__`), create a polished `README.md` (this file) and a CI workflow. Share the GitHub repo URL and I can push changes or create a PR for you.

## License

Add a license file if you intend to publish publicly (MIT/Apache2 recommended for examples).

*** End Project Overview ***



