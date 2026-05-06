from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=255, examples=["Mechanical Keyboard"])
    description: str = Field(default="", max_length=2000, examples=["Hot-swappable RGB keyboard"])
    category: str = Field(min_length=2, max_length=120, examples=["electronics"])
    price: Decimal = Field(gt=0, examples=[129.99])

    @field_validator("name", "category")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ProductCreate(ProductBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Mechanical Keyboard",
                "description": "Hot-swappable RGB keyboard with tactile switches",
                "category": "electronics",
                "price": 129.99,
            }
        }
    }


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255, examples=["Updated Keyboard"])
    description: str | None = Field(default=None, max_length=2000, examples=["Updated description"])
    category: str | None = Field(default=None, min_length=2, max_length=120, examples=["accessories"])
    price: Decimal | None = Field(default=None, gt=0, examples=[149.99])

    @field_validator("name", "category")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Mechanical Keyboard Pro",
                "price": 149.99,
            }
        }
    }


class ProductResponse(ORMModel):
    id: int
    name: str
    description: str
    category: str
    price: Decimal
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    offset: int
    limit: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "name": "Mechanical Keyboard",
                        "description": "Hot-swappable RGB keyboard",
                        "category": "electronics",
                        "price": "129.99",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 10,
            }
        }
    }
