from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class AllowedStrategy(str, Enum):
    BUYER_REQUESTED_DISCOUNT = "BUYER_REQUESTED_DISCOUNT"
    DIRECT_MATCH = "DIRECT_MATCH"
    VOLUME_DISCOUNT = "VOLUME_DISCOUNT"
    BUNDLE_OVERSTOCK = "BUNDLE_OVERSTOCK"
    PRODUCT_SUBSTITUTE = "PRODUCT_SUBSTITUTE"
    QUANTITY_ADJUSTMENT = "QUANTITY_ADJUSTMENT"
    DELIVERY_TRADEOFF = "DELIVERY_TRADEOFF"

class OfferItemDetail(BaseModel):
    sku: str
    name: str
    category: str
    quantity: int
    unit_price_rupees: int
    total_price_rupees: int
    unit_cost_rupees: int
    total_cost_rupees: int
    is_overstock: bool = False

class OfferCandidate(BaseModel):
    candidate_id: str
    strategy: AllowedStrategy
    explanation: str
    items: List[OfferItemDetail]
    total_price_rupees: int
    total_cost_rupees: int
    margin_percent: float
    discount_percent: float
    overstock_items_count: int
    overstock_ratio: float
