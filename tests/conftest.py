import os


# Ensure app settings can be constructed during test collection even when CI
# does not provide database environment variables. Tests that require a real
# PostgreSQL connection still decide at runtime whether to run or skip.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/product_catalog_test",
)
