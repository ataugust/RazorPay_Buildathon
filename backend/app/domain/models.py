"""Deprecated compatibility imports for the former mixed model module.

API schemas now live in ``app.domain.schemas`` and SQLAlchemy database models
live in ``app.db.models``.  New code must import from those modules directly.
"""

from app.domain.schemas import BuyerRequest, BuyerRequestItem

__all__ = ["BuyerRequest", "BuyerRequestItem"]
