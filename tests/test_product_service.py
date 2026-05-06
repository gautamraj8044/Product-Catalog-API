import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.repositories.product import ProductQuery
from app.schemas.product import ProductCreate, ProductListResponse, ProductResponse, ProductUpdate
from app.services.product import ProductService


class FakeProductRepository:
    def __init__(self) -> None:
        self.product = None
        self.deleted = True
        self.created_payload = None

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

    async def get_by_id(self, product_id: int):
        return self.product

    async def create(self, *, name: str, description: str, category: str, price: Decimal):
        self.created_payload = {
            "name": name,
            "description": description,
            "category": category,
            "price": price,
        }
        self.product = type(
            "ProductStub",
            (),
            {
                "id": 2,
                "name": name,
                "description": description,
                "category": category,
                "price": price,
                "created_at": datetime(2024, 1, 1, tzinfo=UTC),
                "updated_at": datetime(2024, 1, 1, tzinfo=UTC),
            },
        )()
        return self.product

    async def delete(self, product_id: int) -> bool:
        return self.deleted


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed = []

    async def commit(self):
        self.commits += 1

    async def refresh(self, instance):
        self.refreshed.append(instance)


class FakeCacheService:
    class settings:
        product_list_cache_ttl_seconds = 120

    def __init__(self):
        self.calls = 0
        self.invalidations = 0

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

    async def invalidate_products(self):
        self.invalidations += 1


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


@pytest.mark.asyncio
async def test_get_product_returns_product_response():
    repository = FakeProductRepository()
    repository.product = type(
        "ProductStub",
        (),
        {
            "id": 1,
            "name": "Keyboard",
            "description": "RGB keyboard",
            "category": "electronics",
            "price": Decimal("129.99"),
            "created_at": datetime(2024, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2024, 1, 1, tzinfo=UTC),
        },
    )()
    service = ProductService(FakeSession(), repository, FakeCacheService())

    response = await service.get_product(1)

    assert isinstance(response, ProductResponse)
    assert response.id == 1


@pytest.mark.asyncio
async def test_get_product_raises_404_when_missing():
    service = ProductService(FakeSession(), FakeProductRepository(), FakeCacheService())

    with pytest.raises(HTTPException) as exc_info:
        await service.get_product(999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Product not found."


@pytest.mark.asyncio
async def test_create_product_commits_and_invalidates_cache():
    session = FakeSession()
    repository = FakeProductRepository()
    cache = FakeCacheService()
    service = ProductService(session, repository, cache)

    response = await service.create_product(
        ProductCreate(
            name="Mechanical Keyboard",
            description="Hot-swappable RGB keyboard",
            category="electronics",
            price=Decimal("129.99"),
        )
    )

    assert response.name == "Mechanical Keyboard"
    assert repository.created_payload is not None
    assert session.commits == 1
    assert cache.invalidations == 1


@pytest.mark.asyncio
async def test_update_product_updates_fields_refreshes_and_invalidates_cache():
    session = FakeSession()
    repository = FakeProductRepository()
    repository.product = type(
        "ProductStub",
        (),
        {
            "id": 3,
            "name": "Keyboard",
            "description": "RGB keyboard",
            "category": "electronics",
            "price": Decimal("129.99"),
            "created_at": datetime(2024, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2024, 1, 1, tzinfo=UTC),
        },
    )()
    cache = FakeCacheService()
    service = ProductService(session, repository, cache)

    response = await service.update_product(
        3,
        ProductUpdate(name="Keyboard Pro", price=Decimal("149.99")),
    )

    assert response.name == "Keyboard Pro"
    assert response.price == Decimal("149.99")
    assert repository.product.name == "Keyboard Pro"
    assert session.commits == 1
    assert session.refreshed == [repository.product]
    assert cache.invalidations == 1


@pytest.mark.asyncio
async def test_update_product_raises_404_when_missing():
    service = ProductService(FakeSession(), FakeProductRepository(), FakeCacheService())

    with pytest.raises(HTTPException) as exc_info:
        await service.update_product(999, ProductUpdate(name="Keyboard Pro"))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Product not found."


@pytest.mark.asyncio
async def test_delete_product_commits_and_invalidates_cache():
    session = FakeSession()
    repository = FakeProductRepository()
    cache = FakeCacheService()
    service = ProductService(session, repository, cache)

    await service.delete_product(4)

    assert session.commits == 1
    assert cache.invalidations == 1


@pytest.mark.asyncio
async def test_delete_product_raises_404_when_missing():
    session = FakeSession()
    repository = FakeProductRepository()
    repository.deleted = False
    cache = FakeCacheService()
    service = ProductService(session, repository, cache)

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_product(999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Product not found."
    assert session.commits == 0
    assert cache.invalidations == 0
