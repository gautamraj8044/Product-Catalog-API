from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Product Catalog API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./product_catalog.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    product_list_cache_ttl_seconds: int = 120

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
