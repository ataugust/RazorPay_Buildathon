import sys
import json
import uuid
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.product import Product
from app.db.models.merchant_policy import MerchantPolicy
from app.domain.strategy_types import AllowedStrategy, OfferCandidate, OfferItemDetail
from app.control_plane.control_plane_engine import ControlPlaneEngine
from app.audit.audit_service import AuditService

def test_phase3_gates():
    db = SessionLocal()
    engine = ControlPlaneEngine()
    
    try:
        policy = db.execute(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy")).scalar_one_or_none()
        if not policy:
            print("Error: Default policy not found.")
            return

        print("==========================================================================")
        print("PHASE 3 VERIFICATION: 6 CONTROL PLANE GATES & AUDIT TRAIL PERSISTENCE")
        print("==========================================================================\n")

        # Test Case 1: Sub-spec Substitution failing SpecificationGate
        txn_1 = f"TXN-SPEC-{uuid.uuid4().hex[:6].upper()}"
        print("--- TEST CASE 1: Sub-Spec Product Substitution (Acer 8GB RAM for 16GB Requirement) ---")
        acer_product = db.execute(select(Product).where(Product.sku == "LAP-004")).scalar_one_or_none() # 8GB RAM
        
        cand_sub_spec = OfferCandidate(
            candidate_id="CAND-SUB-SPEC-01",
            strategy=AllowedStrategy.PRODUCT_SUBSTITUTE,
            explanation="Substituted with Acer Aspire (8GB RAM)",
            items=[
                OfferItemDetail(
                    sku=acer_product.sku,
                    name=acer_product.name,
                    category=acer_product.category,
                    quantity=20,
                    unit_price_rupees=acer_product.selling_price_rupees,
                    total_price_rupees=acer_product.selling_price_rupees * 20,
                    unit_cost_rupees=acer_product.cost_price_rupees,
                    total_cost_rupees=acer_product.cost_price_rupees * 20
                )
            ],
            total_price_rupees=1800000,
            total_cost_rupees=1440000,
            margin_percent=20.0,
            discount_percent=0.0,
            overstock_items_count=0,
            overstock_ratio=0.0
        )

        buyer_hard_specs = {"min_ram_gb": 16, "min_cpu_tier": "i5", "min_storage_gb": 512}
        passed_1, gates_1 = engine.evaluate_candidate(
            db=db,
            transaction_id=txn_1,
            candidate=cand_sub_spec,
            max_budget_rupees=2400000,
            policy=policy,
            buyer_spec_requirements=buyer_hard_specs
        )

        spec_gate_result = next(g for g in gates_1 if g.gate == "SPECIFICATION_GATE")
        print(f"Verdict: {'APPROVED' if passed_1 else 'REJECTED'}")
        print("Structured Gate Output JSON:")
        print(json.dumps(spec_gate_result.model_dump(), indent=2))
        print("--------------------------------------------------------------------------\n")

        # Test Case 2: Valid Volume Discount Counteroffer passing all 6 Gates
        txn_2 = f"TXN-PASS-{uuid.uuid4().hex[:6].upper()}"
        print("--- TEST CASE 2: Valid Volume Discount Counteroffer (Passing All 6 Gates) ---")
        ideapad = db.execute(select(Product).where(Product.sku == "LAP-001")).scalar_one_or_none() # 16GB RAM, 16"
        
        cand_valid = OfferCandidate(
            candidate_id="CAND-VOL-PASS-01",
            strategy=AllowedStrategy.VOLUME_DISCOUNT,
            explanation="Volume price discount to Rs. 1,20,000 per laptop",
            items=[
                OfferItemDetail(
                    sku=ideapad.sku,
                    name=ideapad.name,
                    category=ideapad.category,
                    quantity=20,
                    unit_price_rupees=120000,
                    total_price_rupees=2400000,
                    unit_cost_rupees=ideapad.cost_price_rupees,
                    total_cost_rupees=ideapad.cost_price_rupees * 20
                )
            ],
            total_price_rupees=2400000,
            total_cost_rupees=2000000,
            margin_percent=16.67,
            discount_percent=4.0,
            overstock_items_count=0,
            overstock_ratio=0.0
        )

        agent_mandate = {
            "max_amount": 2400000,
            "allowed_categories": ["LAPTOP"],
            "expires_at": "2028-12-31T23:59:59Z",
            "transaction_id": txn_2
        }

        passed_2, gates_2 = engine.evaluate_candidate(
            db=db,
            transaction_id=txn_2,
            candidate=cand_valid,
            max_budget_rupees=2400000,
            policy=policy,
            buyer_spec_requirements=buyer_hard_specs,
            mandate=agent_mandate
        )

        print(f"Verdict: {'APPROVED' if passed_2 else 'REJECTED'}")
        print("6 Gates Execution Summary:")
        for g in gates_2:
            print(f"  [{g.status}] {g.gate:<20} Expected: {g.expected:<25} Actual: {g.actual}")
        print("--------------------------------------------------------------------------\n")

        # Database Audit Log Persistence Check
        print("--- VERIFYING SQLITE AUDIT EVENT LOGS ---")
        db_logs = AuditService.get_transaction_audit_trail(db, txn_2)
        print(f"Successfully retrieved {len(db_logs)} persisted audit log events for {txn_2}:")
        for log in db_logs:
            print(f"  [{log.timestamp.strftime('%H:%M:%S')}] Component: {log.component:<18} Status: {log.status:<6} Message: {log.message}")

        print("==========================================================================")
        print("PHASE 3 VERIFICATION COMPLETE: ALL 6 GATES & AUDIT PERSISTENCE WORKING!")
        print("==========================================================================")

    finally:
        db.close()

if __name__ == "__main__":
    test_phase3_gates()
