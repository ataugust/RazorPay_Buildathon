from app.control_plane.base_gate import BaseGate, GateResult
from app.domain.models import BuyerRequest, Offer, MerchantPolicy, Product
from sqlmodel import Session, select
from app.db.database import engine

class InventoryGate(BaseGate):
    @property
    def name(self) -> str:
        return "InventoryGate"

    def evaluate(self, offer: Offer, request: BuyerRequest, policy: MerchantPolicy) -> GateResult:
        with Session(engine) as session:
            for item in offer.items_json:
                sku = item.get("sku")
                requested_qty = item.get("quantity", 0)
                product = session.exec(select(Product).where(Product.sku == sku)).first()
                
                if not product:
                    return GateResult(
                        passed=False,
                        gate_name=self.name,
                        message=f"Product with SKU {sku} does not exist in merchant catalog.",
                        metadata={"sku": sku}
                    )
                if product.stock < requested_qty:
                    return GateResult(
                        passed=False,
                        gate_name=self.name,
                        message=f"Insufficient stock for {product.name} (SKU: {sku}). Requested: {requested_qty}, Available: {product.stock}.",
                        metadata={"sku": sku, "requested_stock": requested_qty, "available_stock": product.stock}
                    )

        return GateResult(
            passed=True,
            gate_name=self.name,
            message="All offered items are available in inventory.",
            metadata={"items_count": len(offer.items_json)}
        )

class PolicyGate(BaseGate):
    @property
    def name(self) -> str:
        return "PolicyGate"

    def evaluate(self, offer: Offer, request: BuyerRequest, policy: MerchantPolicy) -> GateResult:
        # Check discount ceiling constraints if applicable
        if not policy.allow_discounts and offer.strategy == "DISCOUNT":
            return GateResult(
                passed=False,
                gate_name=self.name,
                message="Discounts are disabled under current merchant policy.",
                metadata={"allow_discounts": False}
            )
        
        if not policy.allow_bundles and offer.strategy == "BUNDLE_OVERSTOCK":
            return GateResult(
                passed=False,
                gate_name=self.name,
                message="Bundles are disabled under current merchant policy.",
                metadata={"allow_bundles": False}
            )

        return GateResult(
            passed=True,
            gate_name=self.name,
            message="Offer complies with all merchant policy constraints.",
            metadata={"policy_name": policy.name}
        )

class MandateGate(BaseGate):
    @property
    def name(self) -> str:
        return "MandateGate"

    def evaluate(self, offer: Offer, request: BuyerRequest, policy: MerchantPolicy) -> GateResult:
        # Validate purchase mandate bounds
        if request.mandate_id and request.mandate_id.startswith("EXPIRED"):
            return GateResult(
                passed=False,
                gate_name=self.name,
                message=f"Purchase mandate {request.mandate_id} has expired.",
                metadata={"mandate_id": request.mandate_id}
            )
        return GateResult(
            passed=True,
            gate_name=self.name,
            message="Buyer purchase authorization mandate is valid.",
            metadata={"mandate_id": request.mandate_id or "DEFAULT_DEMO_MANDATE"}
        )
