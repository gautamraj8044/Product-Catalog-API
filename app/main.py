from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from sqlalchemy import select

try:
    from redis.asyncio import Redis
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal environments
    Redis = Any  # type: ignore[misc, assignment]

from app.api.routes.auth import router as auth_router
from app.api.routes.products import router as products_router
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import User, UserRole
from app.db.session import AsyncSessionLocal, engine

settings = get_settings()
redis_client: Redis | None = None


async def seed_users() -> None:
    async with AsyncSessionLocal() as session:
        existing_admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
        existing_user = await session.scalar(select(User).where(User.email == "user@example.com"))

        if existing_admin is None:
            session.add(
                User(
                    email="admin@example.com",
                    hashed_password=hash_password("AdminPass123!"),
                    role=UserRole.ADMIN,
                )
            )
        if existing_user is None:
            session.add(
                User(
                    email="user@example.com",
                    hashed_password=hash_password("UserPass123!"),
                    role=UserRole.USER,
                )
            )
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    await seed_users()

    try:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
        await redis_client.ping()
    except Exception:
        redis_client = None

    yield

    if redis_client is not None:
        await redis_client.aclose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Async Product Catalog API with JWT authentication, RBAC, repository/service separation, "
        "Redis cache-aside caching, and paginated product search."
    ),
    lifespan=lifespan,
)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(products_router, prefix=settings.api_prefix)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["info"]["x-logo"] = {"url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"}
    schema["info"]["description"] += (
        "\n\nAuthentication flow:\n"
        "1. Call `POST /api/v1/auth/login` with email and password.\n"
        "2. Copy the returned access token.\n"
        "3. Click `Authorize` in Swagger UI and paste only the access token, not `Bearer <token>`."
    )
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
