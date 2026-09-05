"""Deprecated seed entry point retained for compatibility."""

import warnings

from app.db.bootstrap import bootstrap_database


def seed_data() -> None:
    warnings.warn(
        "app.db.seed.seed_data is deprecated; use app.db.bootstrap.bootstrap_database",
        DeprecationWarning,
        stacklevel=2,
    )
    bootstrap_database()

if __name__ == "__main__":
    seed_data()
