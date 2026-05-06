from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Select, asc, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Product


@dataclass(slots=True)
class ProductQuery:
    offset: int
    limit: int
    search: str | None = None
    category: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


class ProductRepository:
    sortable_fields = {
        "name": Product.name,
        "price": Product.price,
        "category": Product.category,
        "created_at": Product.created_at,
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _apply_filters(self, statement: Select[tuple[Product]], query: ProductQuery) -> Select[tuple[Product]]:
        if query.search:
            term = f"%{query.search.strip()}%"
            statement = statement.where(Product.name.ilike(term) | Product.description.ilike(term))
        if query.category:
            statement = statement.where(Product.category == query.category)
        if query.min_price is not None:
            statement = statement.where(Product.price >= query.min_price)
        if query.max_price is not None:
            statement = statement.where(Product.price <= query.max_price)
        return statement

    def _apply_sorting(self, statement: Select[tuple[Product]], query: ProductQuery) -> Select[tuple[Product]]:
        column = self.sortable_fields.get(query.sort_by, Product.created_at)
        ordering = asc(column) if query.sort_order == "asc" else desc(column)
        return statement.order_by(ordering, desc(Product.id))

    async def list(self, query: ProductQuery) -> tuple[list[Product], int]:
        base_statement = self._apply_filters(select(Product), query)
        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_result = await self.session.execute(count_statement)
        total = total_result.scalar_one()

        list_statement = self._apply_sorting(base_statement, query).offset(query.offset).limit(query.limit)
        result = await self.session.execute(list_statement)
        return list(result.scalars().all()), total

    async def get_by_id(self, product_id: int) -> Product | None:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def create(
        self, *, name: str, description: str, category: str, price: Decimal
    ) -> Product:
        product = Product(name=name, description=description, category=category, price=price)
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def delete(self, product_id: int) -> bool:
        result = await self.session.execute(delete(Product).where(Product.id == product_id))
        return (result.rowcount or 0) > 0
