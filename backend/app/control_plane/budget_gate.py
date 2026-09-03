from app.control_plane.base_gate import BaseGate, GateResult
from app.domain.models import BuyerRequest, Offer, MerchantPolicy

class BudgetGate(BaseGate):
    @property
    def name(self) -> str:
        return "BudgetGate"

    def evaluate(self, offer: Offer, request: BuyerRequest, policy: MerchantPolicy) -> GateResult:
        if offer.total_price_paise <= request.max_budget_paise:
            diff_paise = request.max_budget_paise - offer.total_price_paise
            return GateResult(
                passed=True,
                gate_name=self.name,
                message=f"Offer total ₹{offer.total_price_paise/100:,.2f} is within maximum buyer budget ₹{request.max_budget_paise/100:,.2f}.",
                metadata={"offer_total_paise": offer.total_price_paise, "max_budget_paise": request.max_budget_paise, "savings_paise": diff_paise}
            )
        else:
            excess_paise = offer.total_price_paise - request.max_budget_paise
            return GateResult(
                passed=False,
                gate_name=self.name,
                message=f"Offer total ₹{offer.total_price_paise/100:,.2f} exceeds buyer maximum budget ₹{request.max_budget_paise/100:,.2f} by ₹{excess_paise/100:,.2f}.",
                metadata={"offer_total_paise": offer.total_price_paise, "max_budget_paise": request.max_budget_paise, "excess_paise": excess_paise}
            )
