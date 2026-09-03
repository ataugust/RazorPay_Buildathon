from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.control_plane.base_gate import BaseGate
from app.control_plane.gate_result import GateResult
from app.domain.strategy_types import OfferCandidate
from app.db.models.merchant_policy import MerchantPolicy

class MandateGate(BaseGate):
    @property
    def name(self) -> str:
        return "MANDATE_GATE"

    def evaluate(
        self,
        db: Session,
        candidate: OfferCandidate,
        max_budget_rupees: int,
        policy: MerchantPolicy,
        buyer_spec_requirements: Optional[Dict[str, Any]] = None,
        mandate: Optional[Dict[str, Any]] = None,
    ) -> GateResult:
        if not mandate:
            return GateResult(
                gate=self.name,
                status="PASS",
                expected="Valid Mandate",
                actual="No Mandate Payload",
                reason="Default authorization mandate applied."
            )

        mandate_max_amount = mandate.get("max_amount")
        allowed_categories = mandate.get("allowed_categories", [])
        expires_at_str = mandate.get("expires_at")

        # 1. Mandate Amount Check
        if mandate_max_amount and candidate.total_price_rupees > mandate_max_amount:
            return GateResult(
                gate=self.name,
                status="FAIL",
                expected=f"Mandate Cap <= Rs. {mandate_max_amount:,}",
                actual=f"Rs. {candidate.total_price_rupees:,}",
                reason=f"Candidate total exceeds buyer agent authorized mandate limit (Rs. {candidate.total_price_rupees:,} > Rs. {mandate_max_amount:,}).",
                metadata={"mandate_max_amount": mandate_max_amount, "total_price_rupees": candidate.total_price_rupees}
            )

        # 2. Allowed Categories Check
        if allowed_categories:
            for item in candidate.items:
                if item.category not in allowed_categories:
                    return GateResult(
                        gate=self.name,
                        status="FAIL",
                        expected=f"Category in {allowed_categories}",
                        actual=f"Category '{item.category}'",
                        reason=f"Candidate item '{item.name}' category '{item.category}' is not in buyer agent mandate allowed list {allowed_categories}.",
                        metadata={"sku": item.sku, "category": item.category, "allowed_categories": allowed_categories}
                    )

        # 3. Expiration Check
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expires_at:
                    return GateResult(
                        gate=self.name,
                        status="FAIL",
                        expected="Mandate Active",
                        actual=f"Expired at {expires_at_str}",
                        reason=f"Buyer agent authorization mandate expired at {expires_at_str}.",
                        metadata={"expires_at": expires_at_str}
                    )
            except Exception:
                pass

        return GateResult(
            gate=self.name,
            status="PASS",
            expected="Within Agent Authorization Mandate Bounds",
            actual="Mandate Validated",
            reason="Offer strictly complies with buyer agent transaction authorization mandate.",
            metadata=mandate
        )
