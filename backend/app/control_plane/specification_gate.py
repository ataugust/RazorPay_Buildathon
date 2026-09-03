from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.control_plane.base_gate import BaseGate
from app.control_plane.gate_result import GateResult
from app.domain.strategy_types import OfferCandidate
from app.db.models.merchant_policy import MerchantPolicy
from app.db.models.product import Product

class SpecificationGate(BaseGate):
    @property
    def name(self) -> str:
        return "SPECIFICATION_GATE"

    def evaluate(
        self,
        db: Session,
        candidate: OfferCandidate,
        max_budget_rupees: int,
        policy: MerchantPolicy,
        buyer_spec_requirements: Optional[Dict[str, Any]] = None,
        mandate: Optional[Dict[str, Any]] = None,
    ) -> GateResult:
        if not buyer_spec_requirements:
            return GateResult(
                gate=self.name,
                status="PASS",
                expected="No hard specs required",
                actual="None Specified",
                reason="No explicit technical specification constraints provided by buyer."
            )

        min_ram_gb = buyer_spec_requirements.get("min_ram_gb")
        min_storage_gb = buyer_spec_requirements.get("min_storage_gb")
        required_cpu_tier = buyer_spec_requirements.get("min_cpu_tier")

        for item in candidate.items:
            # We evaluate specs for laptop/hardware products
            if item.category != "LAPTOP":
                continue

            product = db.execute(select(Product).where(Product.sku == item.sku)).scalar_one_or_none()
            if not product:
                continue

            # RAM check
            if min_ram_gb and (product.ram_gb is None or product.ram_gb < min_ram_gb):
                return GateResult(
                    gate=self.name,
                    status="FAIL",
                    expected=f"RAM >= {min_ram_gb}GB",
                    actual=f"{product.ram_gb or 0}GB RAM",
                    reason=f"Substituted product {product.name} (SKU: {product.sku}) violates buyer RAM specification ({product.ram_gb or 0}GB < {min_ram_gb}GB).",
                    metadata={"sku": product.sku, "expected_ram": min_ram_gb, "actual_ram": product.ram_gb}
                )

            # Storage check
            if min_storage_gb and (product.storage_gb is None or product.storage_gb < min_storage_gb):
                return GateResult(
                    gate=self.name,
                    status="FAIL",
                    expected=f"Storage >= {min_storage_gb}GB",
                    actual=f"{product.storage_gb or 0}GB Storage",
                    reason=f"Substituted product {product.name} (SKU: {product.sku}) violates buyer Storage specification ({product.storage_gb or 0}GB < {min_storage_gb}GB).",
                    metadata={"sku": product.sku, "expected_storage": min_storage_gb, "actual_storage": product.storage_gb}
                )

            # CPU tier check (e.g. i5 vs i3)
            if required_cpu_tier and product.cpu_tier:
                # Basic hierarchy check (i7 > i5 > i3)
                tier_rank = {"i3": 1, "i5": 2, "i7": 3, "i9": 4}
                req_rank = tier_rank.get(required_cpu_tier.lower(), 0)
                actual_rank = tier_rank.get(product.cpu_tier.lower(), 0)
                if actual_rank < req_rank:
                    return GateResult(
                        gate=self.name,
                        status="FAIL",
                        expected=f"CPU >= {required_cpu_tier}",
                        actual=f"CPU {product.cpu_tier}",
                        reason=f"Substituted product {product.name} (SKU: {product.sku}) violates CPU tier requirement ({product.cpu_tier} < {required_cpu_tier}).",
                        metadata={"sku": product.sku, "expected_cpu": required_cpu_tier, "actual_cpu": product.cpu_tier}
                    )

        return GateResult(
            gate=self.name,
            status="PASS",
            expected="RAM/CPU/Storage satisfy buyer constraints",
            actual="All Specs Compliant",
            reason="All offered products meet or exceed buyer hardware specification constraints.",
            metadata=buyer_spec_requirements
        )
