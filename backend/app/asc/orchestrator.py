import uuid
from typing import Dict, Any, Tuple, Optional
from sqlmodel import Session, select
from app.db.database import engine
from app.domain.models import BuyerRequest, Offer, MerchantPolicy, OfferStatus, EventStatus, AuditEvent
from app.control_plane.engine import ControlPlaneEngine
from app.asc.candidate_generator import CandidateGenerator
from app.audit.service import AuditService

class ASCOrchestrator:
    def __init__(self):
        self.control_plane = ControlPlaneEngine()
        self.audit_service = AuditService()

    def process_purchase_request(self, request: BuyerRequest) -> Dict[str, Any]:
        transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        
        # Audit: Intent Received
        self.audit_service.log_event(
            transaction_id=transaction_id,
            component="INTENT_PARSER",
            event_type="INTENT_RECEIVED",
            status=EventStatus.INFO,
            message=f"Received purchase intent for {request.items[0].quantity}x {request.items[0].product_query} with budget ₹{request.max_budget_paise/100:,.2f}.",
            metadata={"max_budget_paise": request.max_budget_paise}
        )

        # Get Merchant Policy
        with Session(engine) as session:
            policy = session.exec(select(MerchantPolicy)).first()
            if not policy:
                policy = MerchantPolicy()

        # Step 1: Direct Catalog Match Attempt
        direct_offer = CandidateGenerator.generate_direct_offer(request, transaction_id)
        if direct_offer:
            passed, gate_results = self.control_plane.evaluate_offer(direct_offer, request, policy)
            
            # Log gate checks
            for gr in gate_results:
                self.audit_service.log_event(
                    transaction_id=transaction_id,
                    component="CONTROL_PLANE",
                    event_type=f"GATE_CHECK_{gr.gate_name.upper()}",
                    status=EventStatus.PASS if gr.passed else EventStatus.FAIL,
                    message=gr.message,
                    metadata=gr.metadata
                )

            if passed:
                direct_offer.status = OfferStatus.APPROVED
                self.audit_service.log_event(
                    transaction_id=transaction_id,
                    component="ASC_ORCHESTRATOR",
                    event_type="DIRECT_OFFER_APPROVED",
                    status=EventStatus.PASS,
                    message="Direct catalog match succeeded. Offer approved.",
                    metadata={"offer_id": direct_offer.offer_id}
                )
                return {
                    "transaction_id": transaction_id,
                    "rescued": False,
                    "offer": direct_offer,
                    "gate_results": gate_results
                }

        # Step 2: Direct Match Failed -> Transaction At Risk -> ASC Activates
        self.audit_service.log_event(
            transaction_id=transaction_id,
            component="ASC_ORCHESTRATOR",
            event_type="TRANSACTION_AT_RISK",
            status=EventStatus.WARN,
            message="Direct catalog offer failed buyer budget constraints. Transaction at risk! Activating ASC rescue engine.",
            metadata={}
        )

        # Step 3: Generate Candidate Counteroffers
        candidates = CandidateGenerator.generate_candidate_counteroffers(request, transaction_id, policy)
        
        for candidate in candidates:
            passed, gate_results = self.control_plane.evaluate_offer(candidate, request, policy)
            
            for gr in gate_results:
                self.audit_service.log_event(
                    transaction_id=transaction_id,
                    component="CONTROL_PLANE",
                    event_type=f"GATE_CHECK_{gr.gate_name.upper()}",
                    status=EventStatus.PASS if gr.passed else EventStatus.FAIL,
                    message=f"[Candidate {candidate.strategy}] {gr.message}",
                    metadata=gr.metadata
                )

            if passed:
                candidate.status = OfferStatus.APPROVED
                self.audit_service.log_event(
                    transaction_id=transaction_id,
                    component="ASC_ORCHESTRATOR",
                    event_type="TRANSACTION_RESCUED",
                    status=EventStatus.PASS,
                    message=f"Transaction successfully rescued using strategy {candidate.strategy}!",
                    metadata={"offer_id": candidate.offer_id, "strategy": candidate.strategy}
                )
                return {
                    "transaction_id": transaction_id,
                    "rescued": True,
                    "offer": candidate,
                    "gate_results": gate_results
                }

        # Step 4: Graceful Impossible Deal Handling
        self.audit_service.log_event(
            transaction_id=transaction_id,
            component="ASC_ORCHESTRATOR",
            event_type="DEAL_IMPOSSIBLE",
            status=EventStatus.FAIL,
            message="No candidate offer satisfied both buyer constraints and merchant profit policies. Prioritizing merchant safety over bad sale.",
            metadata={}
        )

        return {
            "transaction_id": transaction_id,
            "rescued": False,
            "offer": None,
            "message": "Impossible deal. Deal rejected gracefully to protect merchant profitability."
        }
