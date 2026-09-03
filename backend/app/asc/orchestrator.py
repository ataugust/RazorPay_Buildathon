import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.product import Product
from app.db.models.merchant_policy import MerchantPolicy
from app.domain.models import BuyerRequest
from app.asc.candidate_generators import (
    VolumeDiscountGenerator,
    OverstockBundleGenerator,
    ProductSubstituteGenerator
)
from app.asc.scoring_engine import DeterministicScoringEngine
from app.control_plane.control_plane_engine import ControlPlaneEngine
from app.audit.audit_service import AuditService

class ASCOrchestrator:
    def __init__(self):
        self.control_plane = ControlPlaneEngine()

    def process_purchase_request(self, request: BuyerRequest) -> Dict[str, Any]:
        transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        db = SessionLocal()
        
        try:
            # 1. Fetch Active Merchant Policy
            policy = db.scalars(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy")).first()
            if not policy:
                policy = MerchantPolicy()

            main_item_req = request.items[0] if request.items else None
            if not main_item_req:
                return {"transaction_id": transaction_id, "status": "ERROR", "message": "No items requested"}

            # Log Intent Received
            max_budget_rupees = request.max_budget_paise // 100
            AuditService.log_event(
                db=db,
                transaction_id=transaction_id,
                component="INTENT_PARSER",
                event_type="INTENT_RECEIVED",
                status="INFO",
                message=f"Received buyer prompt for {main_item_req.quantity}x {main_item_req.product_query} with budget cap Rs. {max_budget_rupees:,}.",
                metadata={"max_budget_rupees": max_budget_rupees, "quantity": main_item_req.quantity}
            )

            # Query product from SQLite DB using db.scalars() for model instance
            product = db.scalars(
                select(Product).where(Product.name.contains(main_item_req.product_query))
            ).first()

            if not product:
                return {
                    "transaction_id": transaction_id,
                    "rescued": False,
                    "message": f"Product '{main_item_req.product_query}' not found in merchant catalog."
                }

            # Direct Match Check
            catalog_total_rupees = product.selling_price_rupees * main_item_req.quantity
            direct_match_success = (catalog_total_rupees <= max_budget_rupees) and (product.stock_quantity >= main_item_req.quantity)

            if not direct_match_success:
                AuditService.log_event(
                    db=db,
                    transaction_id=transaction_id,
                    component="ASC_ORCHESTRATOR",
                    event_type="TRANSACTION_AT_RISK",
                    status="WARN",
                    message=f"Direct match failed (Catalog Rs. {catalog_total_rupees:,} > Budget Rs. {max_budget_rupees:,}). Transaction at risk! Activating ASC Strategy Engine.",
                    metadata={"catalog_total_rupees": catalog_total_rupees, "max_budget_rupees": max_budget_rupees}
                )

            # 2. Generate Candidate Counteroffer Strategies
            candidates = []
            cand_vol = VolumeDiscountGenerator.generate(db, product, main_item_req.quantity, max_budget_rupees, policy)
            if cand_vol:
                candidates.append(cand_vol)

            cand_bnd = OverstockBundleGenerator.generate(db, product, main_item_req.quantity, max_budget_rupees, policy)
            if cand_bnd:
                candidates.append(cand_bnd)

            cand_sub = ProductSubstituteGenerator.generate(db, product, main_item_req.quantity, max_budget_rupees, policy)
            if cand_sub:
                candidates.append(cand_sub)

            if not candidates:
                return {
                    "transaction_id": transaction_id,
                    "rescued": False,
                    "message": "No candidate counteroffers could be generated."
                }

            # 3. Deterministic Scoring & Ranking
            ranked_offers = DeterministicScoringEngine.rank_candidates(candidates, max_budget_rupees, policy)
            best_scored_offer = ranked_offers[0]

            # 4. Evaluate Winning Candidate across 6 Control Plane Gates
            buyer_spec_requirements = {"min_ram_gb": 16, "min_cpu_tier": "i5", "min_storage_gb": 512}
            mandate = {
                "max_amount": max_budget_rupees,
                "allowed_categories": ["LAPTOP", "ACCESSORY", "MONITOR"],
                "expires_at": "2028-12-31T23:59:59Z",
                "transaction_id": transaction_id
            }

            passed_all_gates, gate_results = self.control_plane.evaluate_candidate(
                db=db,
                transaction_id=transaction_id,
                candidate=best_scored_offer.candidate,
                max_budget_rupees=max_budget_rupees,
                policy=policy,
                buyer_spec_requirements=buyer_spec_requirements,
                mandate=mandate
            )

            # Format response for frontend
            formatted_offer = {
                "offer_id": best_scored_offer.candidate.candidate_id,
                "transaction_id": transaction_id,
                "strategy": best_scored_offer.candidate.strategy.value,
                "explanation": best_scored_offer.candidate.explanation,
                "total_price_paise": best_scored_offer.candidate.total_price_rupees * 100,
                "margin_percent": best_scored_offer.candidate.margin_percent,
                "discount_percent": best_scored_offer.candidate.discount_percent,
                "final_score": best_scored_offer.final_score,
                "items": [item.model_dump() for item in best_scored_offer.candidate.items]
            }

            return {
                "transaction_id": transaction_id,
                "rescued": passed_all_gates,
                "offer": formatted_offer if passed_all_gates else None,
                "gate_results": [g.model_dump() for g in gate_results],
                "message": "Transaction rescued successfully!" if passed_all_gates else "Transaction rejected by Control Plane."
            }

        finally:
            db.close()
