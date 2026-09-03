from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as SQLField, JSON

# Enums
class StrategyEnum(str, Enum):
    DIRECT_MATCH = "DIRECT_MATCH"
    DISCOUNT = "DISCOUNT"
    BUNDLE_OVERSTOCK = "BUNDLE_OVERSTOCK"
    ALTERNATIVE_PRODUCT = "ALTERNATIVE_PRODUCT"
    QUANTITY_ADJUSTMENT = "QUANTITY_ADJUSTMENT"
    DELIVERY_TRADEOFF = "DELIVERY_TRADEOFF"

class OfferStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    FAILED = "FAILED"

class EventStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INFO = "INFO"
    WARN = "WARN"

# SQLModel DB Models & Pydantic Data Schemas

class Product(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    sku: str = SQLField(index=True, unique=True)
    name: str
    category: str
    selling_price_paise: int  # Integer paise for money safety
    cost_price_paise: int     # Integer paise for margin calculations
    stock: int
    discount_allowed: bool = True

class MerchantPolicy(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(default="default_policy")
    min_margin_percent: float = 15.0  # Floor profit margin %
    allow_discounts: bool = True
    allow_bundles: bool = True
    max_discount_percent: float = 20.0

class BuyerRequestItem(BaseModel):
    product_query: str
    quantity: int
    sku: Optional[str] = None

class BuyerRequest(BaseModel):
    request_id: str
    items: List[BuyerRequestItem]
    max_budget_paise: int
    currency: str = "INR"
    max_delivery_days: Optional[int] = 7
    preferences: List[str] = []
    mandate_id: Optional[str] = None

class OfferItem(BaseModel):
    sku: str
    product_name: str
    quantity: int
    unit_price_paise: int
    total_price_paise: int
    unit_cost_paise: int

class Offer(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    offer_id: str = SQLField(index=True, unique=True)
    transaction_id: str = SQLField(index=True)
    total_price_paise: int
    total_cost_paise: int
    margin_percent: float
    strategy: StrategyEnum
    status: OfferStatus = OfferStatus.PROPOSED
    explanation: Optional[str] = None
    items_json: List[Dict[str, Any]] = SQLField(default_factory=list, sa_type=JSON)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)

class AuditEvent(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)
    transaction_id: str = SQLField(index=True)
    component: str  # e.g., "INTENT_PARSER", "CONTROL_PLANE", "MARGIN_GATE", etc.
    event_type: str # e.g., "GATE_CHECK", "STRATEGY_SELECTION"
    status: EventStatus
    message: str
    metadata_json: Dict[str, Any] = SQLField(default_factory=dict, sa_type=JSON)
