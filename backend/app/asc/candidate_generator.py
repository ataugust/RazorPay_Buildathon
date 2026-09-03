import uuid
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from app.db.database import engine
from app.domain.models import BuyerRequest, Offer, Product, StrategyEnum, OfferStatus, MerchantPolicy

class StrategyGenerator:
    """Selects appropriate commercial strategies based on request constraints."""
    
    @staticmethod
    def select_strategies(direct_match_failed: bool, reason: str) -> List[StrategyEnum]:
        if not direct_match_failed:
            return [StrategyEnum.DIRECT_MATCH]
        
        # When direct match fails due to budget or pricing
        return [
            StrategyEnum.DISCOUNT,
            StrategyEnum.BUNDLE_OVERSTOCK,
            StrategyEnum.QUANTITY_ADJUSTMENT,
        ]

class CandidateGenerator:
    """Generates candidate offers deterministically from catalog and strategy."""

    @staticmethod
    def generate_direct_offer(request: BuyerRequest, transaction_id: str) -> Optional[Offer]:
        with Session(engine) as session:
            items_json = []
            total_price_paise = 0
            total_cost_paise = 0

            for req_item in request.items:
                product = session.exec(
                    select(Product).where(Product.name.contains(req_item.product_query))
                ).first()

                if not product:
                    return None

                item_total_price = product.selling_price_paise * req_item.quantity
                item_total_cost = product.cost_price_paise * req_item.quantity

                total_price_paise += item_total_price
                total_cost_paise += item_total_cost

                items_json.append({
                    "sku": product.sku,
                    "product_name": product.name,
                    "quantity": req_item.quantity,
                    "unit_price_paise": product.selling_price_paise,
                    "total_price_paise": item_total_price,
                    "unit_cost_paise": product.cost_price_paise,
                })

            margin_percent = 0.0
            if total_price_paise > 0:
                margin_percent = ((total_price_paise - total_cost_paise) / total_price_paise) * 100.0

            return Offer(
                offer_id=f"OFFER-{uuid.uuid4().hex[:8].upper()}",
                transaction_id=transaction_id,
                total_price_paise=total_price_paise,
                total_cost_paise=total_cost_paise,
                margin_percent=round(margin_percent, 2),
                strategy=StrategyEnum.DIRECT_MATCH,
                status=OfferStatus.PROPOSED,
                explanation="Standard direct catalog pricing offer.",
                items_json=items_json,
            )

    @staticmethod
    def generate_candidate_counteroffers(
        request: BuyerRequest, 
        transaction_id: str, 
        policy: MerchantPolicy
    ) -> List[Offer]:
        candidates = []
        with Session(engine) as session:
            # Look up requested main product
            main_item_req = request.items[0] if request.items else None
            if not main_item_req:
                return candidates

            product = session.exec(
                select(Product).where(Product.name.contains(main_item_req.product_query))
            ).first()

            if not product:
                return candidates

            # Candidate 1: Volume Discount within budget
            target_unit_price = min(product.selling_price_paise, request.max_budget_paise // main_item_req.quantity)
            if target_unit_price >= product.cost_price_paise:
                discount_price_paise = target_unit_price * main_item_req.quantity
                discount_cost_paise = product.cost_price_paise * main_item_req.quantity
                margin_percent = ((discount_price_paise - discount_cost_paise) / discount_price_paise) * 100.0 if discount_price_paise > 0 else 0.0

                offer_discount = Offer(
                    offer_id=f"OFFER-{uuid.uuid4().hex[:8].upper()}",
                    transaction_id=transaction_id,
                    total_price_paise=discount_price_paise,
                    total_cost_paise=discount_cost_paise,
                    margin_percent=round(margin_percent, 2),
                    strategy=StrategyEnum.DISCOUNT,
                    status=OfferStatus.PROPOSED,
                    explanation=f"Rescued via volume pricing discount to fit buyer budget ₹{request.max_budget_paise/100:,.2f}.",
                    items_json=[{
                        "sku": product.sku,
                        "product_name": product.name,
                        "quantity": main_item_req.quantity,
                        "unit_price_paise": target_unit_price,
                        "total_price_paise": discount_price_paise,
                        "unit_cost_paise": product.cost_price_paise,
                    }]
                )
                candidates.append(offer_discount)

            # Candidate 2: Overstock Accessory Bundle
            accessory = session.exec(select(Product).where(Product.category == "Accessories")).first()
            if accessory and target_unit_price >= product.cost_price_paise:
                bundle_price = discount_price_paise + (accessory.selling_price_paise * main_item_req.quantity // 2)
                if bundle_price <= request.max_budget_paise:
                    bundle_cost = discount_cost_paise + (accessory.cost_price_paise * main_item_req.quantity)
                    bundle_margin = ((bundle_price - bundle_cost) / bundle_price) * 100.0

                    offer_bundle = Offer(
                        offer_id=f"OFFER-{uuid.uuid4().hex[:8].upper()}",
                        transaction_id=transaction_id,
                        total_price_paise=bundle_price,
                        total_cost_paise=bundle_cost,
                        margin_percent=round(bundle_margin, 2),
                        strategy=StrategyEnum.BUNDLE_OVERSTOCK,
                        status=OfferStatus.PROPOSED,
                        explanation=f"Rescued via overstock accessory package bundle.",
                        items_json=[
                            {
                                "sku": product.sku,
                                "product_name": product.name,
                                "quantity": main_item_req.quantity,
                                "unit_price_paise": target_unit_price,
                                "total_price_paise": discount_price_paise,
                                "unit_cost_paise": product.cost_price_paise,
                            },
                            {
                                "sku": accessory.sku,
                                "product_name": accessory.name,
                                "quantity": main_item_req.quantity,
                                "unit_price_paise": accessory.selling_price_paise // 2,
                                "total_price_paise": accessory.selling_price_paise * main_item_req.quantity // 2,
                                "unit_cost_paise": accessory.cost_price_paise,
                            }
                        ]
                    )
                    candidates.append(offer_bundle)

        return candidates
