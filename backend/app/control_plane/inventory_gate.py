from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.control_plane.base_gate import BaseGate
from app.control_plane.gate_result import GateResult
from app.domain.strategy_types import OfferCandidate
from app.db.models.merchant_policy import MerchantPolicy
from app.db.models.product import Product

class InventoryGate(BaseGate):
    @property
    def name(self) -> str:
        return "INVENTORY_GATE"

    def evaluate(
        self,
        db: Session,
        candidate: OfferCandidate,
        max_budget_rupees: int,
        policy: MerchantPolicy,
        buyer_spec_requirements: Optional[Dict[str, Any]] = None,
        mandate: Optional[Dict[str, Any]] = None,
    ) -> GateResult:
        for item in candidate.items:
            product = db.execute(select(Product).where(Product.sku == item.sku)).scalar_one_or_none()
            if not product:
                return GateResult(
                    gate=self.name,
                    status="FAIL",
                    expected=f"SKU {item.sku} exists in catalog",
                    actual="SKU Not Found",
                    reason=f"Product with SKU '{item.sku}' does not exist in inventory.",
                    metadata={"sku": item.sku}
                )

            if item.quantity > product.stock_quantity:
                return GateResult(
                    gate=self.name,
                    status="FAIL",
                    expected=f"Stock >= {item.quantity}",
                    actual=f"Stock = {product.stock_quantity}",
                    reason=f"Insufficient inventory stock for {product.name} (SKU: {item.sku}). Requested: {item.quantity}, Available: {product.stock_quantity}.",
                    metadata={"sku": item.sku, "requested": item.quantity, "available": product.stock_quantity}
                )

        return GateResult(
            gate=self.name,
            status="PASS",
            expected="All offered items in stock",
            actual="In Stock",
            reason="All offered line items are verified in stock.",
            metadata={"items_checked": len(candidate.items)}
        )
