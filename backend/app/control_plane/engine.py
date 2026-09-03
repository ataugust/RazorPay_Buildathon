from typing import List, Tuple
from app.control_plane.base_gate import BaseGate, GateResult
from app.control_plane.budget_gate import BudgetGate
from app.control_plane.margin_gate import MarginGate
from app.control_plane.inventory_gate import InventoryGate, PolicyGate, MandateGate
from app.domain.models import BuyerRequest, Offer, MerchantPolicy

class ControlPlaneEngine:
    def __init__(self):
        self.gates: List[BaseGate] = [
            BudgetGate(),
            MarginGate(),
            InventoryGate(),
            PolicyGate(),
            MandateGate(),
        ]

    def evaluate_offer(self, offer: Offer, request: BuyerRequest, policy: MerchantPolicy) -> Tuple[bool, List[GateResult]]:
        results = []
        all_passed = True

        for gate in self.gates:
            result = gate.evaluate(offer, request, policy)
            results.append(result)
            if not result.passed:
                all_passed = False

        return all_passed, results
