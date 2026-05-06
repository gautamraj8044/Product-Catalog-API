from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_current_user, get_product_service, require_role
from app.db.models import User, UserRole
from app.repositories.product import ProductQuery
from app.schemas.product import ProductCreate, ProductListResponse, ProductResponse, ProductUpdate
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products with pagination, filtering, and sorting",
    description=(
        "Returns a paginated product collection. Results are cached in Redis using a cache-aside "
        "strategy keyed by pagination and filter parameters."
    ),
)
async def list_products(
    response: Response,
    offset: int = Query(default=0, ge=0, examples=[0]),
    limit: int = Query(default=10, ge=1, le=100, examples=[10]),
    search: str | None = Query(default=None, examples=["keyboard"]),
    category: str | None = Query(default=None, examples=["electronics"]),
    min_price: Decimal | None = Query(default=None, ge=0, examples=[50]),
    max_price: Decimal | None = Query(default=None, ge=0, examples=[200]),
    sort_by: Literal["name", "price", "category", "created_at"] = Query(
        default="created_at", examples=["price"]
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", examples=["asc"]),
    current_user: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    query = ProductQuery(
        offset=offset,
        limit=limit,
        search=search,
        category=category,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    payload, cache_audit = await product_service.list_products(query)
    response.headers["X-Cache"] = cache_audit.status
    response.headers["X-Cache-Key"] = cache_audit.key
    response.headers["X-Cache-TTL"] = str(cache_audit.ttl_seconds)
    return payload


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a single product",
)
async def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return await product_service.get_product(product_id)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
async def create_product(
    payload: ProductCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    product_service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return await product_service.create_product(payload)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    product_service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return await product_service.update_product(product_id, payload)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
)
async def delete_product(
    product_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    product_service: ProductService = Depends(get_product_service),
) -> Response:
    await product_service.delete_product(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
