import asyncio
from decimal import Decimal

from app.repositories.product import ProductQuery
from app.schemas.product import ProductListResponse, ProductResponse
from app.services.product import ProductService


class FakeProductRepository:
    async def list(self, query: ProductQuery):
        item = type(
            "ProductStub",
            (),
            {
                "id": 1,
                "name": "Keyboard",
                "description": "RGB keyboard",
                "category": "electronics",
                "price": Decimal("129.99"),
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        )()
        return [item], 1


class FakeSession:
    async def commit(self):
        return None

    async def refresh(self, _):
        return None


class FakeCacheService:
    class settings:
        product_list_cache_ttl_seconds = 120

    def __init__(self):
        self.calls = 0

    async def build_list_key(self, suffix: str) -> str:
        return f"cache:{suffix}"

    async def get_or_set(self, *, key: str, producer):
        self.calls += 1
        if self.calls == 1:
            payload = await producer()
            return payload, "miss"
        return {
            "items": [
                {
                    "id": 1,
                    "name": "Keyboard",
                    "description": "RGB keyboard",
                    "category": "electronics",
                    "price": "129.99",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            ],
            "total": 1,
            "offset": 0,
            "limit": 10,
        }, "hit"


def test_list_products_reports_cache_status():
    async def runner():
        service = ProductService(FakeSession(), FakeProductRepository(), FakeCacheService())
        query = ProductQuery(offset=0, limit=10)

        response_one, audit_one = await service.list_products(query)
        response_two, audit_two = await service.list_products(query)

        assert isinstance(response_one, ProductListResponse)
        assert isinstance(response_two.items[0], ProductResponse)
        assert audit_one.status == "miss"
        assert audit_two.status == "hit"

    asyncio.run(runner())
