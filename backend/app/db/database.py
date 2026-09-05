"""Deprecated compatibility layer for the former SQLModel database module.

New code must import ``engine`` and ``get_db`` from :mod:`app.db.session` and
use Alembic via :mod:`app.db.bootstrap` for schema management.
"""

import warnings

from app.db.bootstrap import run_migrations
from app.db.session import engine, get_db


def init_db() -> None:
    warnings.warn(
        "app.db.database.init_db is deprecated; use app.db.bootstrap.run_migrations",
        DeprecationWarning,
        stacklevel=2,
    )
    run_migrations()


get_session = get_db

__all__ = ["engine", "get_db", "get_session", "init_db"]
