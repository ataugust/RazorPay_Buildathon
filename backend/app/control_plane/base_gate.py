from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.control_plane.gate_result import GateResult
from app.domain.strategy_types import OfferCandidate
from app.db.models.merchant_policy import MerchantPolicy

class BaseGate(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def evaluate(
        self,
        db: Session,
        candidate: OfferCandidate,
        max_budget_rupees: int,
        policy: MerchantPolicy,
        buyer_spec_requirements: Optional[Dict[str, Any]] = None,
        mandate: Optional[Dict[str, Any]] = None,
    ) -> GateResult:
        pass
