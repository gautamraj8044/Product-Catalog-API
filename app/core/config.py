from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Product Catalog API"
    api_prefix: str = "/api/v1"
    database_url: Optional[str] = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: Optional[SecretStr] = None
    postgres_db: str = "product_catalog"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("change-me-in-development"),
        min_length=16,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    product_list_cache_ttl_seconds: int = 120
    bootstrap_admin_email: Optional[str] = None
    bootstrap_admin_password: Optional[SecretStr] = Field(default=None, min_length=8)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if self.database_url:
            return self

        if self.postgres_password is None:
            raise ValueError(
                "Set DATABASE_URL or provide POSTGRES_PASSWORD with the other POSTGRES_* settings."
            )

        self.database_url = (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password.get_secret_value()}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
