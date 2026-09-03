from app.control_plane.base_gate import BaseGate, GateResult
from app.domain.models import BuyerRequest, Offer, MerchantPolicy

class MarginGate(BaseGate):
    @property
    def name(self) -> str:
        return "MarginGate"

    def evaluate(self, offer: Offer, request: BuyerRequest, policy: MerchantPolicy) -> GateResult:
        if offer.total_price_paise == 0:
            return GateResult(
                passed=False,
                gate_name=self.name,
                message="Offer price cannot be zero.",
                metadata={"margin_percent": 0.0}
            )

        margin_percent = offer.margin_percent
        min_floor = policy.min_margin_percent

        if margin_percent >= min_floor:
            return GateResult(
                passed=True,
                gate_name=self.name,
                message=f"Offer profit margin {margin_percent:.2f}% meets or exceeds merchant policy floor {min_floor:.2f}%.",
                metadata={"margin_percent": margin_percent, "min_margin_percent": min_floor}
            )
        else:
            return GateResult(
                passed=False,
                gate_name=self.name,
                message=f"Offer profit margin {margin_percent:.2f}% violates merchant minimum policy floor {min_floor:.2f}%.",
                metadata={"margin_percent": margin_percent, "min_margin_percent": min_floor}
            )
