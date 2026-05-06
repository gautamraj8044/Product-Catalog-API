import json
from collections.abc import Awaitable, Callable
from typing import Any

try:
    from redis.asyncio import Redis
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal environments
    Redis = Any  # type: ignore[misc, assignment]

from app.core.config import get_settings


class CacheService:
    namespace_key = "product_catalog:products:namespace"

    def __init__(self, redis: Redis | None) -> None:
        self.redis = redis
        self.settings = get_settings()

    async def get_namespace(self) -> str:
        if self.redis is None:
            return "0"

        namespace = await self.redis.get(self.namespace_key)
        if namespace is None:
            await self.redis.set(self.namespace_key, "1")
            return "1"
        return namespace.decode() if isinstance(namespace, bytes) else str(namespace)

    async def build_list_key(self, suffix: str) -> str:
        namespace = await self.get_namespace()
        return f"product_catalog:products:v{namespace}:{suffix}"

    async def get_json(self, key: str) -> dict[str, Any] | None:
        if self.redis is None:
            return None
        payload = await self.redis.get(key)
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode()
        return json.loads(payload)

    async def set_json(self, key: str, value: dict[str, Any]) -> None:
        if self.redis is None:
            return
        await self.redis.set(key, json.dumps(value, default=str), ex=self.settings.product_list_cache_ttl_seconds)

    async def get_or_set(
        self, *, key: str, producer: Callable[[], Awaitable[dict[str, Any]]]
    ) -> tuple[dict[str, Any], str]:
        cached = await self.get_json(key)
        if cached is not None:
            return cached, "hit"

        payload = await producer()
        await self.set_json(key, payload)
        return payload, "miss"

    async def invalidate_products(self) -> None:
        if self.redis is None:
            return
        await self.redis.incr(self.namespace_key)
