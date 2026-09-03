from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.control_plane.base_gate import BaseGate
from app.control_plane.gate_result import GateResult
from app.control_plane.margin_gate import MarginGate
from app.control_plane.inventory_gate import InventoryGate
from app.control_plane.budget_gate import BudgetGate
from app.control_plane.discount_gate import DiscountGate
from app.control_plane.specification_gate import SpecificationGate
from app.control_plane.mandate_gate import MandateGate
from app.domain.strategy_types import OfferCandidate
from app.db.models.merchant_policy import MerchantPolicy
from app.audit.audit_service import AuditService

class ControlPlaneEngine:
    def __init__(self):
        self.gates: List[BaseGate] = [
            MarginGate(),
            InventoryGate(),
            BudgetGate(),
            DiscountGate(),
            SpecificationGate(),
            MandateGate(),
        ]

    def evaluate_candidate(
        self,
        db: Session,
        transaction_id: str,
        candidate: OfferCandidate,
        max_budget_rupees: int,
        policy: MerchantPolicy,
        buyer_spec_requirements: Optional[Dict[str, Any]] = None,
        mandate: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[GateResult]]:
        gate_results = []
        all_passed = True

        # Log Gate Evaluation Start
        AuditService.log_event(
            db=db,
            transaction_id=transaction_id,
            component="CONTROL_PLANE",
            event_type="EVALUATION_START",
            status="INFO",
            message=f"Evaluating candidate offer {candidate.candidate_id} ({candidate.strategy.value}) across 6 Control Plane Gates.",
            metadata={"candidate_id": candidate.candidate_id, "strategy": candidate.strategy.value}
        )

        for gate in self.gates:
            result = gate.evaluate(
                db=db,
                candidate=candidate,
                max_budget_rupees=max_budget_rupees,
                policy=policy,
                buyer_spec_requirements=buyer_spec_requirements,
                mandate=mandate,
            )
            gate_results.append(result)

            # Audit log individual gate evaluation
            AuditService.log_event(
                db=db,
                transaction_id=transaction_id,
                component=result.gate,
                event_type=f"GATE_CHECK_{result.status}",
                status=result.status,
                message=f"[{result.gate}] {result.reason} (Expected: {result.expected}, Actual: {result.actual})",
                metadata=result.model_dump()
            )

            if result.status != "PASS":
                all_passed = False

        verdict_status = "APPROVED" if all_passed else "REJECTED"
        AuditService.log_event(
            db=db,
            transaction_id=transaction_id,
            component="CONTROL_PLANE",
            event_type=f"CANDIDATE_{verdict_status}",
            status="PASS" if all_passed else "FAIL",
            message=f"Candidate offer {candidate.candidate_id} was {verdict_status} by Commerce Control Plane.",
            metadata={"candidate_id": candidate.candidate_id, "verdict": verdict_status, "gates_passed": sum(1 for g in gate_results if g.status == "PASS")}
        )

        return all_passed, gate_results
