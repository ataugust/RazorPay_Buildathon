"""Validated contracts shared by all intent-intelligence providers."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.domain.strategy_types import AllowedStrategy


class HardSpecifications(BaseModel):
    min_ram_gb: Optional[int] = Field(default=None, gt=0)
    min_cpu_tier: Optional[str] = None
    min_storage_gb: Optional[int] = Field(default=None, gt=0)


class IntentIntelligence(BaseModel):
    """Non-authoritative interpretation of a buyer's natural-language intent."""

    product_query: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    max_budget_paise: int = Field(gt=0)
    currency: Literal["INR"] = "INR"
    max_delivery_days: Optional[int] = Field(default=7, gt=0)
    hard_specs: HardSpecifications = Field(default_factory=HardSpecifications)
    preferences: List[str] = Field(default_factory=list)
    recommended_strategies: List[AllowedStrategy] = Field(default_factory=list)
    strategy_rationale: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provider: str = "deterministic"
    model: Optional[str] = None
    fallback_reason: Optional[str] = None
