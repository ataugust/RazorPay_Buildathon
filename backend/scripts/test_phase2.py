import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.product import Product
from app.db.models.merchant_policy import MerchantPolicy
from app.asc.candidate_generators import (
    VolumeDiscountGenerator,
    OverstockBundleGenerator,
    ProductSubstituteGenerator
)
from app.asc.scoring_engine import DeterministicScoringEngine

def verify_phase2():
    db = SessionLocal()
    try:
        # Load Merchant Policy
        policy = db.execute(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy")).scalar_one_or_none()
        if not policy:
            print("Error: Default policy not found. Run `python -m scripts.seed_policy` first.")
            return

        print("==================================================")
        print("PHASE 2 VERIFICATION: MERCHANT POLICY & SCORING")
        print("==================================================")
        print(f"Policy Name:         {policy.policy_name}")
        print(f"Min Margin Floor:    {policy.min_margin_percent}%")
        print(f"Max Discount Cap:    {policy.max_discount_percent}%")
        print(f"Scoring Weights:     Margin={policy.weight_margin}, Revenue={policy.weight_revenue}, Overstock={policy.weight_overstock}, DiscountPenalty={policy.weight_discount_penalty}\n")

        # Scenario: Buyer wants 20x Lenovo IdeaPad Pro 16 (SKU: LAP-001)
        # Catalog Selling Price: Rs. 1,25,000 * 20 = Rs. 25,00,000 (Rs. 25L)
        # Buyer Max Authorized Budget: Rs. 24,00,000 (Rs. 24L) -> Direct catalog match fails!
        sku = "LAP-001"
        quantity = 20
        max_budget_rupees = 2400000  # Rs. 24 Lakhs

        requested_product = db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()
        if not requested_product:
            print(f"Error: Product {sku} not found.")
            return

        catalog_total = requested_product.selling_price_rupees * quantity
        print(f"SIMULATED BUYER REQUEST:")
        print(f"  Item Requested:     {quantity}x {requested_product.name} ({requested_product.sku})")
        print(f"  Normal Catalog Val: Rs. {catalog_total:,}")
        print(f"  Buyer Budget Cap:   Rs. {max_budget_rupees:,}")
        print(f"  Direct Match:       FAILED (Rs. {catalog_total:,} > Rs. {max_budget_rupees:,})\n")

        # Generate Candidate Strategies
        candidates = []
        
        # 1. Volume Discount
        cand_vol = VolumeDiscountGenerator.generate(db, requested_product, quantity, max_budget_rupees, policy)
        if cand_vol:
            candidates.append(cand_vol)

        # 2. Overstock Bundle
        cand_bnd = OverstockBundleGenerator.generate(db, requested_product, quantity, max_budget_rupees, policy)
        if cand_bnd:
            candidates.append(cand_bnd)

        # 3. Product Substitution
        cand_sub = ProductSubstituteGenerator.generate(db, requested_product, quantity, max_budget_rupees, policy)
        if cand_sub:
            candidates.append(cand_sub)

        print(f"Generated {len(candidates)} candidate offer strategies.\n")

        # Rank Candidates via Deterministic Scoring Engine
        ranked_offers = DeterministicScoringEngine.rank_candidates(candidates, max_budget_rupees, policy)

        print("DETERMINISTIC RANKING RESULTS:")
        print("---------------------------------------------------------------------------------------------------")
        print(f"{'RANK':<5} | {'STRATEGY':<20} | {'TOTAL (Rs.)':<12} | {'MARGIN %':<9} | {'DISCOUNT %':<10} | {'SCORE':<7}")
        print("---------------------------------------------------------------------------------------------------")
        
        for idx, scored in enumerate(ranked_offers, 1):
            cand = scored.candidate
            print(f"{idx:<5} | {cand.strategy.value:<20} | Rs. {cand.total_price_rupees:<9,} | {cand.margin_percent:<8.2f}% | {cand.discount_percent:<9.2f}% | {scored.final_score:<7.2f}")
            print(f"      Explanation: {cand.explanation}")
            print(f"      Item Details: {[f'{item.quantity}x {item.name} (SKU: {item.sku})' for item in cand.items]}\n")

        winning_offer = ranked_offers[0]
        print("==================================================")
        print(f"WINNING STRATEGY SELECTED: {winning_offer.candidate.strategy.value}")
        print(f"Final Score: {winning_offer.final_score}/100")
        print(f"Total Counteroffer Value: Rs. {winning_offer.candidate.total_price_rupees:,}")
        print("==================================================")

    finally:
        db.close()

if __name__ == "__main__":
    verify_phase2()
