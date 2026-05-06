from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from redis.asyncio import Redis
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal environments
    Redis = None  # type: ignore[assignment]

from app.core.security import decode_token
from app.db.models import User, UserRole
from app.db.session import get_db_session
from app.repositories.product import ProductRepository
from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.services.cache import CacheService
from app.services.product import ProductService

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    bearerFormat="JWT",
    description="Paste the JWT access token returned by the login endpoint.",
    auto_error=False,
)


async def get_redis_client() -> AsyncIterator[Redis | None]:
    from app.main import redis_client

    yield redis_client


async def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(UserRepository(session))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    user = await session.get(User, int(user_id))

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return user


def require_role(*roles: UserRole):
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action.",
            )
        return current_user

    return dependency


async def get_product_service(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis | None = Depends(get_redis_client),
) -> ProductService:
    product_repository = ProductRepository(session)
    cache_service = CacheService(redis)
    return ProductService(session, product_repository, cache_service)
