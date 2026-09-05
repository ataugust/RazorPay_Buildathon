"""Pydantic request/response schemas for the ASC API boundary.

Database tables live exclusively under :mod:`app.db.models`.  Keeping API
schemas here prevents HTTP contracts from accidentally creating SQL tables or
depending on a particular persistence implementation.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class BuyerRequestItem(BaseModel):
    product_query: str
    quantity: int = Field(gt=0)
    sku: Optional[str] = None


class BuyerRequest(BaseModel):
    request_id: str
    items: List[BuyerRequestItem] = Field(min_length=1)
    max_budget_paise: int = Field(gt=0)
    currency: str = "INR"
    max_delivery_days: Optional[int] = Field(default=7, gt=0)
    preferences: List[str] = Field(default_factory=list)
    requested_discount_percent: Optional[float] = Field(default=None, ge=0, le=100)
    mandate_id: Optional[str] = None
