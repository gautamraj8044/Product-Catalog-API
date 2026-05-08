# Product Catalog API

Async Product Catalog API built with FastAPI, SQLAlchemy, JWT authentication, role-based access control, and Redis cache-aside caching.

## Overview

This project provides a small but production-structured backend for managing products. It separates routing, services, repositories, schemas, and database models so the API surface stays simple while the internals remain maintainable.

Core capabilities:

- JWT login for authenticated access
- Optional one-time bootstrap admin creation through environment variables
- Admin-only product create, update, and delete operations
- Admin-only user creation, including creating another admin
- Product listing with pagination, filtering, sorting, and Redis-backed cache-aside behavior
- OpenAPI/Swagger docs with request examples

## Tech Stack

- FastAPI
- SQLAlchemy 2.x async
- PostgreSQL
- Redis
- Pydantic v2
- JWT
- `pwdlib` Argon2 password hashing

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
  test_auth.py
  test_product_service.py
```

## Features

### Authentication and Authorization

- `POST /api/v1/auth/login` returns a Bearer token
- Every product endpoint requires authentication
- Only `admin` users can:
  - create products
  - update products
  - delete products
  - create new user accounts

### Product API

- List products with:
  - `offset`
  - `limit`
  - `search`
  - `category`
  - `min_price`
  - `max_price`
  - `sort_by`
  - `sort_order`
- Retrieve a single product by ID
- Create, update, and delete products

### Caching

- Product list responses use Redis cache-aside caching
- Cache metadata is exposed through response headers:
  - `X-Cache`
  - `X-Cache-Key`
  - `X-Cache-TTL`
- Product mutations invalidate the product list cache namespace

## Bootstrap Admin

The app does not create permanent default credentials.

For first-time setup, you can optionally provide a bootstrap admin through environment variables:

- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD`

If both values are set and no admin user exists yet, the app creates one admin account on startup. If an admin already exists, startup leaves user data unchanged.

## Admin Can Create More Accounts

An authenticated admin can create:

- another admin account
- a normal user account

Endpoint:

```text
POST /api/v1/auth/users
```

Example request:

```json
{
  "email": "new-admin@example.com",
  "password": "StrongPass123!",
  "role": "admin"
}
```

Allowed role values:

- `admin`
- `user`

## API Endpoints

### Auth

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/users` (admin only)

### Products

- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/products` (admin only)
- `PUT /api/v1/products/{product_id}` (admin only)
- `DELETE /api/v1/products/{product_id}` (admin only)

## Quick Start

### Local Development

1. Create a virtual environment.
2. Install dependencies.
3. Copy `.env.example` to `.env`.
4. Start PostgreSQL and Redis if you want the full stack locally.
5. Run the API.

Example:

```bash
docker run --name my-postgres ^
  -e POSTGRES_PASSWORD=<YOUR_POSTGRES_PASSWORD> ^
  -p 5432:5432 ^
  -d postgres:latest

python -m venv .venv
.venv\Scripts\activate
pip install -e .
set POSTGRES_PASSWORD=<YOUR_POSTGRES_PASSWORD>
set BOOTSTRAP_ADMIN_EMAIL=admin@example.com
set BOOTSTRAP_ADMIN_PASSWORD=AdminPass123!
uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Environment Variables

The app reads configuration from `.env`.

```env
APP_NAME=Product Catalog API
API_PREFIX=/api/v1
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_HOST_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
POSTGRES_DB=product_catalog
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
PRODUCT_LIST_CACHE_TTL_SECONDS=120
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=ChangeMe123!
```

## Docker

Run the full stack with Docker Compose:

```bash
docker compose up --build
```

Services:

- API on `http://127.0.0.1:8000`
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

If you already have a local PostgreSQL service on port `5432`, set `POSTGRES_HOST_PORT` to another host port such as `5433`, and set the app's `POSTGRES_PORT` or `DATABASE_URL` to the same host port when connecting from your machine.

The compose setup persists:

- PostgreSQL data in `postgres_data`
- Redis data in `redis_data`

### Docker Hub Deployment Workflow

The repository includes a GitHub Actions workflow at `.github/workflows/docker-publish.yml`.

It publishes the Docker image to Docker Hub when:

- code is pushed to `main` or `master`
- a Git tag like `v0.1.0` is pushed
- the workflow is started manually from GitHub Actions

Required GitHub repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Image tags produced by the workflow:

- `latest` for the default branch
- branch name tags such as `main`
- version tags such as `v0.1.0`
- a commit SHA tag

Before using it, update the image name in `.github/workflows/docker-publish.yml` if you want a different Docker Hub repository path:

```yaml
IMAGE_NAME: ${{ secrets.DOCKERHUB_USERNAME }}/product-catalog-api
```

Example release flow:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Example Usage

### 1. Login

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@example.com\",\"password\":\"<BOOTSTRAP_ADMIN_PASSWORD>\"}"
```

### 2. Create another admin

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/users" ^
  -H "Authorization: Bearer <TOKEN>" ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"second-admin@example.com\",\"password\":\"AdminPass456!\",\"role\":\"admin\"}"
```

### 3. Create a product

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/products" ^
  -H "Authorization: Bearer <TOKEN>" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Mechanical Keyboard\",\"description\":\"Hot-swappable RGB keyboard\",\"category\":\"electronics\",\"price\":129.99}"
```

### 4. List products

```bash
curl "http://127.0.0.1:8000/api/v1/products?limit=10&sort_by=price&sort_order=asc" ^
  -H "Authorization: Bearer <TOKEN>"
```

## Testing

Install dev dependencies and run tests:

```bash
uv sync --extra dev
.venv\Scripts\python -m pytest
```

Current automated coverage includes:

- auth service and admin-only user creation route checks
- product service cache behavior checks

## Notes

- If Redis is unavailable, the app falls back to running without cache instead of failing startup.
- The default JWT secret is for development only and should be replaced in any real deployment.
- `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` must be set together if you use bootstrap admin creation.
- The API expects PostgreSQL and reads connection details from `DATABASE_URL` or the `POSTGRES_*` environment variables.
- Apply schema changes with Alembic before starting the app: `alembic upgrade head`
