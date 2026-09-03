from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.control_plane.base_gate import BaseGate
from app.control_plane.gate_result import GateResult
from app.domain.strategy_types import OfferCandidate
from app.db.models.merchant_policy import MerchantPolicy

class MarginGate(BaseGate):
    @property
    def name(self) -> str:
        return "MARGIN_GATE"

    def evaluate(
        self,
        db: Session,
        candidate: OfferCandidate,
        max_budget_rupees: int,
        policy: MerchantPolicy,
        buyer_spec_requirements: Optional[Dict[str, Any]] = None,
        mandate: Optional[Dict[str, Any]] = None,
    ) -> GateResult:
        expected_str = f">= {policy.min_margin_percent}%"
        actual_str = f"{candidate.margin_percent:.2f}%"

        if candidate.margin_percent >= policy.min_margin_percent:
            return GateResult(
                gate=self.name,
                status="PASS",
                expected=expected_str,
                actual=actual_str,
                reason=f"Offer profit margin ({actual_str}) meets minimum merchant floor ({expected_str}).",
                metadata={"margin_percent": candidate.margin_percent, "min_margin_percent": policy.min_margin_percent}
            )
        else:
            return GateResult(
                gate=self.name,
                status="FAIL",
                expected=expected_str,
                actual=actual_str,
                reason=f"Offer violates merchant minimum profit margin ({actual_str} < {expected_str}).",
                metadata={"margin_percent": candidate.margin_percent, "min_margin_percent": policy.min_margin_percent}
            )
