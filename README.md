# Product Catalog API

Production-ready Product Catalog API built with FastAPI, async SQLAlchemy, JWT authentication, RBAC, and Redis cache-aside caching.

## Features

- JWT authentication with seeded admin and user accounts
- RBAC for product CRUD operations
- Async service and repository layers
- Redis-backed cache-aside strategy for list endpoints
- Pagination, filtering, and sorting
- Rich OpenAPI documentation with examples and auth guidance

## Project Structure

```text
app/
  api/
    dependencies.py
    routes/
      auth.py
      products.py
  core/
    config.py
    security.py
  db/
    base.py
    models.py
    session.py
  repositories/
    product.py
    user.py
  schemas/
    auth.py
    common.py
    product.py
  services/
    auth.py
    cache.py
    product.py
  main.py
tests/
  test_product_service.py
```

## Quick Start

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and adjust values if needed.
3. Run the API:

```bash
uvicorn app.main:app --reload
```

## Seeded Users

- `admin@example.com` / `AdminPass123!`
- `user@example.com` / `UserPass123!`

## Authentication

Use the `/api/v1/auth/login` endpoint to obtain an access token, then authorize from Swagger UI using the `Authorize` button and paste the token value.

Admins can create additional accounts with `POST /api/v1/auth/users` by sending `email`, `password`, and `role` (`admin` or `user`).

## Cache Strategy

- Product list responses are cached in Redis using a cache-aside flow.
- Product mutations invalidate product-list cache keys by namespace version bumping.
- Product detail caching can be added later if read volume justifies it.
