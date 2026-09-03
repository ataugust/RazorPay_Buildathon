from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.control_plane.base_gate import BaseGate
from app.control_plane.gate_result import GateResult
from app.domain.strategy_types import OfferCandidate
from app.db.models.merchant_policy import MerchantPolicy

class DiscountGate(BaseGate):
    @property
    def name(self) -> str:
        return "DISCOUNT_GATE"

    def evaluate(
        self,
        db: Session,
        candidate: OfferCandidate,
        max_budget_rupees: int,
        policy: MerchantPolicy,
        buyer_spec_requirements: Optional[Dict[str, Any]] = None,
        mandate: Optional[Dict[str, Any]] = None,
    ) -> GateResult:
        expected_str = f"<= {policy.max_discount_percent}%"
        actual_str = f"{candidate.discount_percent:.2f}%"

        if candidate.discount_percent <= policy.max_discount_percent:
            return GateResult(
                gate=self.name,
                status="PASS",
                expected=expected_str,
                actual=actual_str,
                reason=f"Candidate discount ({actual_str}) is within permitted merchant policy cap ({expected_str}).",
                metadata={"discount_percent": candidate.discount_percent, "max_discount_percent": policy.max_discount_percent}
            )
        else:
            return GateResult(
                gate=self.name,
                status="FAIL",
                expected=expected_str,
                actual=actual_str,
                reason=f"Candidate discount ({actual_str}) exceeds permitted merchant policy maximum ({expected_str}).",
                metadata={"discount_percent": candidate.discount_percent, "max_discount_percent": policy.max_discount_percent}
            )
