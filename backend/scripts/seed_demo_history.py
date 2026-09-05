"""Replace test transactions with credible, internally consistent demo history."""
import argparse
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select
from app.db.session import SessionLocal
from app.db.models import AuditEvent, Product
from app.db.models.agent_message import AgentMessage
from app.db.models.buyer_draft import BuyerDraft
from app.db.models.deal import Deal


STRATEGIES = ["VOLUME_DISCOUNT", "PRODUCT_SUBSTITUTE", "BUNDLE_OVERSTOCK"]


def offer(product, quantity, discount, transaction_id, strategy):
    unit = round(product.selling_price_rupees * (1 - discount / 100))
    total = unit * quantity
    cost = product.cost_price_rupees * quantity
    margin = round((total - cost) / total * 100, 2)
    return {
        "offer_id": f"OFF-{transaction_id}", "transaction_id": transaction_id,
        "strategy": strategy, "explanation": f"Policy-safe {strategy.lower().replace('_', ' ')} recovered the order.",
        "total_price_paise": total * 100, "margin_percent": margin,
        "discount_percent": discount, "final_score": 78.0 + (quantity % 17),
        "items": [{"sku": product.sku, "name": product.name, "category": product.category,
            "quantity": quantity, "unit_price_rupees": unit, "total_price_rupees": total,
            "unit_cost_rupees": product.cost_price_rupees, "total_cost_rupees": cost,
            "is_overstock": product.is_overstock}],
    }


def seed_demo_history(confirm=False):
    if not confirm:
        raise SystemExit("Refusing to replace transaction history without --confirm")
    with SessionLocal() as db:
        products = db.scalars(select(Product).where(Product.is_active.is_(True))).all()
        eligible = [p for p in products if p.selling_price_rupees > p.cost_price_rupees]
        if len(eligible) < 6:
            raise RuntimeError("Seed the product catalog before creating demo history.")
        db.execute(delete(AgentMessage))
        db.execute(delete(AuditEvent))
        db.execute(delete(BuyerDraft))
        db.execute(delete(Deal))
        now = datetime.now(timezone.utc)
        recovered_count, direct_count, lost_count = 28, 8, 2
        for index in range(recovered_count + direct_count + lost_count):
            transaction_id = f"DEMO-{index + 1:04d}"
            product = eligible[index % len(eligible)]
            quantity = 2 + (index * 3) % 18
            created = now - timedelta(hours=(recovered_count + direct_count + lost_count - index) * 7)
            is_recovered = index < recovered_count
            is_direct = recovered_count <= index < recovered_count + direct_count
            strategy = STRATEGIES[index % len(STRATEGIES)] if is_recovered else "DIRECT_MATCH"
            discount = float(3 + index % 5) if is_recovered else 0.0
            current = offer(product, quantity, discount, transaction_id, strategy) if not (not is_recovered and not is_direct) else None
            if current and current["margin_percent"] < 12:
                current = offer(product, quantity, 0.0, transaction_id, strategy)
            status = "COMPLETED" if current else "LOST"
            budget = (current["total_price_paise"] if current else product.selling_price_rupees * quantity * 70)
            candidates = []
            if current:
                candidates.append({"strategy": strategy, "name": strategy.replace("_", " ").title(),
                    "total_price_paise": current["total_price_paise"],
                    "total_cost_paise": sum(i["total_cost_rupees"] for i in current["items"]) * 100,
                    "margin_percent": current["margin_percent"], "discount_percent": current["discount_percent"],
                    "score": current["final_score"], "status": "WINNER",
                    "note": current["explanation"], "gate_results": []})
            gates = [{"gate": name, "status": "PASS", "expected": "Merchant policy", "actual": "Verified",
                "reason": "Demo transaction passed the persisted deterministic control evidence.", "metadata": {}}
                for name in ("MARGIN_GATE", "INVENTORY_GATE", "BUDGET_GATE", "DISCOUNT_GATE", "SPECIFICATION_GATE", "MANDATE_GATE")] if current else []
            reply = (
                f"We supplied {quantity} × {product.name} for ₹{current['total_price_paise'] / 100:,.2f}."
                if current else "No eligible offer was available within the requested constraints."
            )
            deal = Deal(
                transaction_id=transaction_id, title=f"{product.name} procurement",
                prompt=f"Purchase {quantity} {product.name} units for our team.",
                product_query=product.name, quantity=quantity, max_budget_paise=budget,
                status=status, outcome_type="RECOVERED" if is_recovered else "DIRECT_MATCH" if is_direct else "REJECTED",
                recovered=is_recovered, intelligence_json={"provider": "demo_history", "product_query": product.name,
                    "quantity": quantity, "hard_specs": {}, "preferences": [], "recommended_strategies": [strategy]},
                initial_offer_json=current, current_offer_json=current, candidates_json=candidates,
                gate_results_json=gates, merchant_response_json={"response_type": "OFFER_AVAILABLE" if current else "NO_FEASIBLE_OFFER",
                    "message": reply, "inventory_available": True, "requested_budget_paise": budget, "policy_reasons": []},
                created_at=created, updated_at=created + timedelta(minutes=4),
                completed_at=created + timedelta(minutes=4) if current else None,
            )
            db.add(deal)
            db.flush()
            db.add_all([
                AgentMessage(transaction_id=transaction_id, sender="BUYER_AGENT", recipient="MERCHANT_AGENT",
                    message_type="PURCHASE_REQUEST", content=f"Request for {quantity} × {product.name}.", metadata_json={}),
                AgentMessage(transaction_id=transaction_id, sender="MERCHANT_AGENT", recipient="BUYER_AGENT",
                    message_type="PROPOSAL" if current else "UNABLE_TO_OFFER", content=reply, metadata_json={}),
                AuditEvent(transaction_id=transaction_id, timestamp=created, component="INTENT_PARSER",
                    event_type="INTENT_RECEIVED", status="INFO", message="Buyer request received.", metadata_json={}),
                AuditEvent(transaction_id=transaction_id, timestamp=created + timedelta(minutes=2), component="CONTROL_PLANE",
                    event_type="CANDIDATE_APPROVED" if current else "CANDIDATE_REJECTED",
                    status="PASS" if current else "FAIL",
                    message="All controls passed." if current else "No candidate satisfied all controls.", metadata_json={}),
            ])
        db.commit()
    print(f"Demo history created: {recovered_count} recovered, {direct_count} direct, {lost_count} lost.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    seed_demo_history(parser.parse_args().confirm)
