from dataclasses import dataclass
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.product import ProductQuery, ProductRepository
from app.schemas.product import ProductCreate, ProductListResponse, ProductResponse, ProductUpdate
from app.services.cache import CacheService


@dataclass(slots=True)
class CacheAudit:
    status: str
    key: str
    ttl_seconds: int


class ProductService:
    def __init__(
        self,
        session: AsyncSession,
        product_repository: ProductRepository,
        cache_service: CacheService,
    ) -> None:
        self.session = session
        self.product_repository = product_repository
        self.cache_service = cache_service

    async def list_products(self, query: ProductQuery) -> tuple[ProductListResponse, CacheAudit]:
        query_params = urlencode(
            {
                "offset": query.offset,
                "limit": query.limit,
                "search": query.search or "",
                "category": query.category or "",
                "min_price": query.min_price if query.min_price is not None else "",
                "max_price": query.max_price if query.max_price is not None else "",
                "sort_by": query.sort_by,
                "sort_order": query.sort_order,
            }
        )
        cache_key = await self.cache_service.build_list_key(query_params)

        async def producer() -> dict[str, object]:
            items, total = await self.product_repository.list(query)
            response = ProductListResponse(
                items=[ProductResponse.model_validate(item) for item in items],
                total=total,
                offset=query.offset,
                limit=query.limit,
            )
            return response.model_dump(mode="json")

        payload, cache_status = await self.cache_service.get_or_set(key=cache_key, producer=producer)
        response = ProductListResponse.model_validate(payload)
        audit = CacheAudit(
            status=cache_status,
            key=cache_key,
            ttl_seconds=self.cache_service.settings.product_list_cache_ttl_seconds,
        )
        return response, audit

    async def get_product(self, product_id: int) -> ProductResponse:
        product = await self.product_repository.get_by_id(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
        return ProductResponse.model_validate(product)

    async def create_product(self, payload: ProductCreate) -> ProductResponse:
        product = await self.product_repository.create(**payload.model_dump())
        await self.session.commit()
        await self.cache_service.invalidate_products()
        return ProductResponse.model_validate(product)

    async def update_product(self, product_id: int, payload: ProductUpdate) -> ProductResponse:
        product = await self.product_repository.get_by_id(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

        updates = payload.model_dump(exclude_none=True)
        for field, value in updates.items():
            setattr(product, field, value)

        await self.session.commit()
        await self.session.refresh(product)
        await self.cache_service.invalidate_products()
        return ProductResponse.model_validate(product)

    async def delete_product(self, product_id: int) -> None:
        deleted = await self.product_repository.delete(product_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
        await self.session.commit()
        await self.cache_service.invalidate_products()
