import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.product import Product
from app.db.models.merchant_policy import MerchantPolicy
from app.domain.schemas import BuyerRequest
from app.domain.strategy_types import AllowedStrategy
from app.llm.contracts import IntentIntelligence
from app.asc.candidate_generators import (
    DirectMatchGenerator,
    VolumeDiscountGenerator,
    OverstockBundleGenerator,
    ProductSubstituteGenerator
    , BuyerRequestedDiscountGenerator
)
from app.asc.scoring_engine import DeterministicScoringEngine
from app.control_plane.control_plane_engine import ControlPlaneEngine
from app.audit.audit_service import AuditService
from app.asc.catalog_search import find_products

class ASCOrchestrator:
    def __init__(self):
        self.control_plane = ControlPlaneEngine()

    def process_purchase_request(
        self,
        request: BuyerRequest,
        intelligence: Optional[IntentIntelligence] = None,
    ) -> Dict[str, Any]:
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

            if intelligence:
                AuditService.log_event(
                    db=db,
                    transaction_id=transaction_id,
                    component="INTELLIGENCE_LAYER",
                    event_type="INTENT_NORMALIZED",
                    status="INFO",
                    message=(
                        f"Intent normalized by {intelligence.provider}; proposed "
                        f"{len(intelligence.recommended_strategies)} bounded strategies."
                    ),
                    metadata={
                        "provider": intelligence.provider,
                        "model": intelligence.model,
                        "confidence": intelligence.confidence,
                        "recommended_strategies": [
                            strategy.value for strategy in intelligence.recommended_strategies
                        ],
                        "fallback_reason": intelligence.fallback_reason,
                    },
                )

            # Query product from SQLite DB using db.scalars() for model instance
            matches = find_products(db, main_item_req.product_query, intelligence.hard_specs.model_dump(exclude_none=True) if intelligence else {})
            product = next((p for p in matches if p.stock_quantity >= main_item_req.quantity), matches[0] if matches else None)

            if not product:
                return {
                    "transaction_id": transaction_id,
                    "rescued": False,
                    "offer": None,
                    "gate_results": [],
                    "message": f"Product '{main_item_req.product_query}' not found in merchant catalog."
                }

            # Direct Match Check
            catalog_total_rupees = product.selling_price_rupees * main_item_req.quantity
            direct_match_success = (catalog_total_rupees <= max_budget_rupees) and (product.stock_quantity >= main_item_req.quantity)

            if not direct_match_success:
                price_exceeds_budget = catalog_total_rupees > max_budget_rupees
                insufficient_stock = product.stock_quantity < main_item_req.quantity
                if price_exceeds_budget and insufficient_stock:
                    risk_reason = (
                        f"catalog total Rs. {catalog_total_rupees:,} exceeds budget Rs. {max_budget_rupees:,} "
                        f"and only {product.stock_quantity} units are in stock"
                    )
                elif price_exceeds_budget:
                    risk_reason = f"catalog total Rs. {catalog_total_rupees:,} exceeds budget Rs. {max_budget_rupees:,}"
                else:
                    risk_reason = f"requested {main_item_req.quantity} units but only {product.stock_quantity} are in stock"
                AuditService.log_event(
                    db=db,
                    transaction_id=transaction_id,
                    component="ASC_ORCHESTRATOR",
                    event_type="TRANSACTION_AT_RISK",
                    status="WARN",
                    message=f"Direct match failed because {risk_reason}. Activating the ASC Strategy Engine.",
                    metadata={
                        "catalog_total_rupees": catalog_total_rupees,
                        "max_budget_rupees": max_budget_rupees,
                        "requested_quantity": main_item_req.quantity,
                        "stock_quantity": product.stock_quantity,
                        "price_exceeds_budget": price_exceeds_budget,
                        "insufficient_stock": insufficient_stock,
                    }
                )

            # 2. Generate candidates in deterministic Python. Intelligence may
            # narrow this allow-list, but it cannot construct commercial values.
            candidates = []
            requested_candidate = None
            if request.requested_discount_percent is not None:
                requested_candidate = BuyerRequestedDiscountGenerator.generate(
                    db, product, main_item_req.quantity, max_budget_rupees, policy,
                    request.requested_discount_percent,
                )
                if requested_candidate:
                    candidates.append(requested_candidate)
            if direct_match_success:
                direct = DirectMatchGenerator.generate(
                    db, product, main_item_req.quantity, max_budget_rupees, policy
                )
                if direct:
                    candidates.append(direct)
            else:
                recommended = set(
                    intelligence.recommended_strategies if intelligence else [
                        AllowedStrategy.VOLUME_DISCOUNT,
                        AllowedStrategy.BUNDLE_OVERSTOCK,
                        AllowedStrategy.PRODUCT_SUBSTITUTE,
                    ]
                )
                if not recommended:
                    recommended = {
                        AllowedStrategy.VOLUME_DISCOUNT,
                        AllowedStrategy.BUNDLE_OVERSTOCK,
                        AllowedStrategy.PRODUCT_SUBSTITUTE,
                    }
                generators = {
                    AllowedStrategy.VOLUME_DISCOUNT: VolumeDiscountGenerator,
                    AllowedStrategy.BUNDLE_OVERSTOCK: OverstockBundleGenerator,
                    AllowedStrategy.PRODUCT_SUBSTITUTE: ProductSubstituteGenerator,
                }
                for strategy, generator in generators.items():
                    if intelligence and strategy == AllowedStrategy.PRODUCT_SUBSTITUTE and "alternative_products_allowed" not in intelligence.preferences:
                        continue
                    if intelligence and strategy == AllowedStrategy.BUNDLE_OVERSTOCK and "bundles_preferred" not in intelligence.preferences:
                        continue
                    if strategy in recommended:
                        candidate = generator.generate(
                            db, product, main_item_req.quantity, max_budget_rupees, policy
                        )
                        if candidate:
                            candidates.append(candidate)

            # A generic category can contain many SKUs. Evaluate every matching
            # product; the first name match must never determine availability.
            for matched in matches:
                if matched.stock_quantity < main_item_req.quantity:
                    continue
                direct = DirectMatchGenerator.generate(db, matched, main_item_req.quantity, max_budget_rupees, policy)
                discount = VolumeDiscountGenerator.generate(db, matched, main_item_req.quantity, max_budget_rupees, policy)
                for candidate in (direct, discount):
                    if candidate and not any(c.items[0].sku == candidate.items[0].sku and c.strategy == candidate.strategy for c in candidates):
                        candidates.append(candidate)

            if not candidates:
                AuditService.log_event(
                    db=db,
                    transaction_id=transaction_id,
                    component="ASC_ORCHESTRATOR",
                    event_type="STRATEGY_EXHAUSTED",
                    status="WARN",
                    message="No deterministic candidate could be generated from the bounded strategy set.",
                    metadata={
                        "recommended_strategies": [
                            strategy.value for strategy in recommended
                        ] if not direct_match_success else [AllowedStrategy.DIRECT_MATCH.value]
                    },
                )
                return {
                    "transaction_id": transaction_id,
                    "rescued": False,
                    "offer": None,
                    "gate_results": [],
                    "message": "No candidate counteroffers could be generated."
                    , "catalog_total_paise": catalog_total_rupees * 100
                }

            # 3. Deterministic Scoring & Ranking
            ranked_offers = DeterministicScoringEngine.rank_candidates(candidates, max_budget_rupees, policy)
            best_scored_offer = ranked_offers[0]
            evaluated_by_id = {}
            formatted_candidates = [
                {
                    "strategy": scored.candidate.strategy.value,
                    "name": scored.candidate.strategy.value.replace("_", " ").title(),
                    "total_price_paise": scored.candidate.total_price_rupees * 100,
                    "total_cost_paise": scored.candidate.total_cost_rupees * 100,
                    "margin_percent": scored.candidate.margin_percent,
                    "discount_percent": scored.candidate.discount_percent,
                    "score": scored.final_score,
                    "status": (
                        "WINNER"
                        if scored.candidate.candidate_id == best_scored_offer.candidate.candidate_id
                        else "REJECTED_MARGIN"
                        if not scored.passes_min_margin
                        else "ALTERNATIVE"
                    ),
                    "note": scored.candidate.explanation,
                    "gate_results": [],
                }
                for scored in ranked_offers
            ]

            # 4. Evaluate Winning Candidate across 6 Control Plane Gates
            buyer_spec_requirements = (
                intelligence.hard_specs.model_dump(exclude_none=True)
                if intelligence
                else {"min_ram_gb": 16, "min_cpu_tier": "i5", "min_storage_gb": 512}
            )
            mandate = {
                "max_amount": max_budget_rupees,
                "allowed_categories": ["LAPTOP", "ACCESSORY", "MONITOR"],
                "expires_at": "2028-12-31T23:59:59Z",
                "transaction_id": transaction_id
            }

            requested_scored = next((s for s in ranked_offers if requested_candidate and s.candidate.candidate_id == requested_candidate.candidate_id), None)
            evaluation_order = ([requested_scored] if requested_scored else []) + [s for s in ranked_offers if s is not requested_scored]
            passed_all_gates = False
            gate_results = []
            for evaluated in evaluation_order:
                passed, results = self.control_plane.evaluate_candidate(
                        db=db, transaction_id=transaction_id, candidate=evaluated.candidate,
                        max_budget_rupees=max_budget_rupees, policy=policy,
                        buyer_spec_requirements=buyer_spec_requirements, mandate=mandate,
                )
                evaluated_by_id[evaluated.candidate.candidate_id] = results
                if passed:
                    best_scored_offer, passed_all_gates, gate_results = evaluated, True, results
                    break
            direct_match_success = best_scored_offer.candidate.strategy == AllowedStrategy.DIRECT_MATCH
            for row, scored in zip(formatted_candidates, ranked_offers):
                candidate_results = evaluated_by_id.get(scored.candidate.candidate_id, [])
                row["gate_results"] = [g.model_dump() for g in candidate_results]
                rejected_by_gate = any(g.status == "FAIL" for g in candidate_results)
                row["status"] = "WINNER" if passed_all_gates and scored == best_scored_offer else "REJECTED_POLICY" if rejected_by_gate else "REJECTED_MARGIN" if not scored.passes_min_margin else "ALTERNATIVE"

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
                "outcome_type": (
                    "DIRECT_MATCH"
                    if direct_match_success and passed_all_gates
                    else "RESCUED_COUNTEROFFER"
                    if passed_all_gates
                    else "REJECTED"
                ),
                "direct_match": direct_match_success,
                "catalog_total_paise": catalog_total_rupees * 100,
                "offer": formatted_offer if passed_all_gates else None,
                "candidates": formatted_candidates,
                "gate_results": [g.model_dump() for g in gate_results],
                "message": (
                    "Catalog offer approved; negotiation was not required."
                    if direct_match_success and passed_all_gates
                    else "Transaction rescued with a policy-compliant counteroffer."
                    if passed_all_gates
                    else "Transaction rejected by Control Plane."
                )
            }

        finally:
            db.close()
