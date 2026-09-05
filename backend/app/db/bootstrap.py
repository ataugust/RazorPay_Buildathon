"""Database migration and reference-data bootstrap for ASC."""

from alembic import command
from alembic.config import Config

from app.core.config import BACKEND_DIR, DATABASE_URL


def run_migrations() -> None:
    """Upgrade the authoritative SQLAlchemy database to the latest revision."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(config, "head")


def seed_reference_data() -> None:
    """Idempotently seed products and merchant policies."""
    # Imports are intentionally deferred until migrations have created tables.
    from scripts.seed_policy import seed_policies
    from scripts.seed_products import seed_products

    seed_products(update_existing=False)
    seed_policies(update_existing=False)


def bootstrap_database() -> None:
    run_migrations()
    seed_reference_data()
