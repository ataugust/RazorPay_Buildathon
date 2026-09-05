import uuid
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.product import Product
from app.db.models.merchant_policy import MerchantPolicy
from app.domain.strategy_types import AllowedStrategy, OfferCandidate, OfferItemDetail

class DirectMatchGenerator:
    """Builds a catalog-price offer when stock and budget already permit it."""

    @staticmethod
    def generate(
        db: Session,
        requested_product: Product,
        quantity: int,
        max_budget_rupees: int,
        policy: MerchantPolicy,
    ) -> Optional[OfferCandidate]:
        total_price = requested_product.selling_price_rupees * quantity
        total_cost = requested_product.cost_price_rupees * quantity
        if requested_product.stock_quantity < quantity or total_price > max_budget_rupees:
            return None
        margin_percent = round(((total_price - total_cost) / total_price) * 100.0, 2)
        return OfferCandidate(
            candidate_id=f"CAND-DIR-{uuid.uuid4().hex[:6].upper()}",
            strategy=AllowedStrategy.DIRECT_MATCH,
            explanation=f"Catalog offer for {quantity}x {requested_product.name}; no negotiated pricing required.",
            items=[OfferItemDetail(
                sku=requested_product.sku,
                name=requested_product.name,
                category=requested_product.category,
                quantity=quantity,
                unit_price_rupees=requested_product.selling_price_rupees,
                total_price_rupees=total_price,
                unit_cost_rupees=requested_product.cost_price_rupees,
                total_cost_rupees=total_cost,
                is_overstock=requested_product.is_overstock,
            )],
            total_price_rupees=total_price,
            total_cost_rupees=total_cost,
            margin_percent=margin_percent,
            discount_percent=0.0,
            overstock_items_count=0,
            overstock_ratio=0.0,
        )

class BuyerRequestedDiscountGenerator:
    """Materialize the buyer's exact discount request so policy can judge it."""

    @staticmethod
    def generate(
        db: Session,
        requested_product: Product,
        quantity: int,
        max_budget_rupees: int,
        policy: MerchantPolicy,
        requested_discount_percent: float,
    ) -> Optional[OfferCandidate]:
        if requested_product.stock_quantity < quantity:
            return None
        ratio = (Decimal("100") - Decimal(str(requested_discount_percent))) / Decimal("100")
        unit_price = int((Decimal(requested_product.selling_price_rupees) * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        total_price = unit_price * quantity
        total_cost = requested_product.cost_price_rupees * quantity
        if unit_price <= 0 or total_price > max_budget_rupees:
            return None
        actual_discount = round(
            (requested_product.selling_price_rupees - unit_price) / requested_product.selling_price_rupees * 100,
            2,
        )
        margin = round((total_price - total_cost) / total_price * 100, 2)
        return OfferCandidate(
            candidate_id=f"CAND-REQ-{uuid.uuid4().hex[:6].upper()}",
            strategy=AllowedStrategy.BUYER_REQUESTED_DISCOUNT,
            explanation=(
                f"Buyer requested {requested_discount_percent:g}% off. The exact candidate is "
                "submitted to deterministic policy gates before it can become an offer."
            ),
            items=[OfferItemDetail(
                sku=requested_product.sku, name=requested_product.name,
                category=requested_product.category, quantity=quantity,
                unit_price_rupees=unit_price, total_price_rupees=total_price,
                unit_cost_rupees=requested_product.cost_price_rupees,
                total_cost_rupees=total_cost, is_overstock=requested_product.is_overstock,
            )],
            total_price_rupees=total_price, total_cost_rupees=total_cost,
            margin_percent=margin, discount_percent=actual_discount,
            overstock_items_count=0, overstock_ratio=0.0,
        )

class RecoveryDiscountGenerator:
    """Creates a deterministic post-rejection discount within merchant policy."""

    @staticmethod
    def generate(
        db: Session,
        requested_product: Product,
        quantity: int,
        max_budget_rupees: int,
        policy: MerchantPolicy,
        preferred_discount_percent: float = 5.0,
    ) -> Optional[OfferCandidate]:
        discount_percent = min(preferred_discount_percent, policy.max_discount_percent)
        unit_price = int(requested_product.selling_price_rupees * (1 - discount_percent / 100.0))
        total_price = unit_price * quantity
        total_cost = requested_product.cost_price_rupees * quantity
        if total_price > max_budget_rupees or total_price <= total_cost:
            return None
        margin_percent = round(((total_price - total_cost) / total_price) * 100.0, 2)
        actual_discount = round(
            ((requested_product.selling_price_rupees - unit_price) / requested_product.selling_price_rupees) * 100.0,
            2,
        )
        return OfferCandidate(
            candidate_id=f"CAND-REC-{uuid.uuid4().hex[:6].upper()}",
            strategy=AllowedStrategy.VOLUME_DISCOUNT,
            explanation=(
                f"Applied a policy-capped {actual_discount}% recovery discount after buyer rejection; "
                "all monetary values were calculated deterministically."
            ),
            items=[OfferItemDetail(
                sku=requested_product.sku,
                name=requested_product.name,
                category=requested_product.category,
                quantity=quantity,
                unit_price_rupees=unit_price,
                total_price_rupees=total_price,
                unit_cost_rupees=requested_product.cost_price_rupees,
                total_cost_rupees=total_cost,
                is_overstock=requested_product.is_overstock,
            )],
            total_price_rupees=total_price,
            total_cost_rupees=total_cost,
            margin_percent=margin_percent,
            discount_percent=actual_discount,
            overstock_items_count=0,
            overstock_ratio=0.0,
        )

class VolumeDiscountGenerator:
    """Generates a candidate offer with a volume price discount to fit the buyer's budget cap."""

    @staticmethod
    def generate(
        db: Session,
        requested_product: Product,
        quantity: int,
        max_budget_rupees: int,
        policy: MerchantPolicy
    ) -> Optional[OfferCandidate]:
        original_total_price = requested_product.selling_price_rupees * quantity
        original_total_cost = requested_product.cost_price_rupees * quantity

        # If direct match already fits within budget, no discount needed here
        if original_total_price <= max_budget_rupees:
            return None

        # Calculate unit target price required to meet max_budget
        target_unit_price = max_budget_rupees // quantity

        # Check maximum discount ceiling constraint from merchant policy
        min_allowed_unit_price = math.ceil(requested_product.selling_price_rupees * (1 - policy.max_discount_percent / 100.0))
        discounted_unit_price = max(target_unit_price, min_allowed_unit_price)

        discounted_total_price = discounted_unit_price * quantity
        
        # Calculate margin & discount %
        margin_percent = round(((discounted_total_price - original_total_cost) / discounted_total_price) * 100.0, 2) if discounted_total_price > 0 else 0.0
        discount_percent = round(((original_total_price - discounted_total_price) / original_total_price) * 100.0, 2)

        return OfferCandidate(
            candidate_id=f"CAND-VOL-{uuid.uuid4().hex[:6].upper()}",
            strategy=AllowedStrategy.VOLUME_DISCOUNT,
            explanation=f"Applied {discount_percent}% volume pricing discount on {quantity}x {requested_product.name} to align with target budget Rs. {max_budget_rupees:,}.",
            items=[
                OfferItemDetail(
                    sku=requested_product.sku,
                    name=requested_product.name,
                    category=requested_product.category,
                    quantity=quantity,
                    unit_price_rupees=discounted_unit_price,
                    total_price_rupees=discounted_total_price,
                    unit_cost_rupees=requested_product.cost_price_rupees,
                    total_cost_rupees=original_total_cost,
                    is_overstock=requested_product.is_overstock
                )
            ],
            total_price_rupees=discounted_total_price,
            total_cost_rupees=original_total_cost,
            margin_percent=margin_percent,
            discount_percent=discount_percent,
            overstock_items_count=0,
            overstock_ratio=0.0
        )

class OverstockBundleGenerator:
    """Generates a candidate offer combining discounted main item with high-margin overstock accessories."""

    @staticmethod
    def generate(
        db: Session,
        requested_product: Product,
        quantity: int,
        max_budget_rupees: int,
        policy: MerchantPolicy
    ) -> Optional[OfferCandidate]:
        if not policy.allow_bundles:
            return None

        # Query active overstock items (e.g. accessories)
        overstock_items = db.scalars(
            select(Product)
            .where(Product.is_overstock == True)
            .where(Product.is_active == True)
            .where(Product.stock_quantity >= quantity)
        ).all()

        if not overstock_items:
            return None

        # Pick best overstock accessory
        accessory = overstock_items[0]

        # Calculate discounted main item price
        target_unit_price = max_budget_rupees // quantity
        main_unit_price = int(target_unit_price * 0.95)  # 5% below target budget to make room for accessory
        
        main_total_price = main_unit_price * quantity
        main_total_cost = requested_product.cost_price_rupees * quantity

        acc_unit_price = accessory.selling_price_rupees // 2  # 50% bundle discount on accessory
        acc_total_price = acc_unit_price * quantity
        acc_total_cost = accessory.cost_price_rupees * quantity

        bundle_total_price = main_total_price + acc_total_price
        bundle_total_cost = main_total_cost + acc_total_cost

        if bundle_total_price > max_budget_rupees:
            # Adjust accessory price down so total fits budget
            acc_total_price = max_budget_rupees - main_total_price
            bundle_total_price = main_total_price + acc_total_price

        margin_percent = round(((bundle_total_price - bundle_total_cost) / bundle_total_price) * 100.0, 2) if bundle_total_price > 0 else 0.0
        original_val = (requested_product.selling_price_rupees + accessory.selling_price_rupees) * quantity
        discount_percent = round(((original_val - bundle_total_price) / original_val) * 100.0, 2)

        return OfferCandidate(
            candidate_id=f"CAND-BND-{uuid.uuid4().hex[:6].upper()}",
            strategy=AllowedStrategy.BUNDLE_OVERSTOCK,
            explanation=f"Bundled {quantity}x {requested_product.name} with overstock {quantity}x {accessory.name} at special bundle pricing.",
            items=[
                OfferItemDetail(
                    sku=requested_product.sku,
                    name=requested_product.name,
                    category=requested_product.category,
                    quantity=quantity,
                    unit_price_rupees=main_unit_price,
                    total_price_rupees=main_total_price,
                    unit_cost_rupees=requested_product.cost_price_rupees,
                    total_cost_rupees=main_total_cost,
                    is_overstock=False
                ),
                OfferItemDetail(
                    sku=accessory.sku,
                    name=accessory.name,
                    category=accessory.category,
                    quantity=quantity,
                    unit_price_rupees=acc_unit_price,
                    total_price_rupees=acc_total_price,
                    unit_cost_rupees=accessory.cost_price_rupees,
                    total_cost_rupees=acc_total_cost,
                    is_overstock=True
                )
            ],
            total_price_rupees=bundle_total_price,
            total_cost_rupees=bundle_total_cost,
            margin_percent=margin_percent,
            discount_percent=discount_percent,
            overstock_items_count=quantity,
            overstock_ratio=0.5
        )

class ProductSubstituteGenerator:
    """Generates a candidate offer using an alternative product in the same category within budget."""

    @staticmethod
    def generate(
        db: Session,
        requested_product: Product,
        quantity: int,
        max_budget_rupees: int,
        policy: MerchantPolicy
    ) -> Optional[OfferCandidate]:
        if not policy.allow_substitutions:
            return None

        # Look up alternative products in the same category whose catalog price fits within max_budget
        substitutes = db.scalars(
            select(Product)
            .where(Product.category == requested_product.category)
            .where(Product.id != requested_product.id)
            .where(Product.is_active == True)
            .where(Product.stock_quantity >= quantity)
            .where((Product.selling_price_rupees * quantity) <= max_budget_rupees)
            .order_by(Product.selling_price_rupees.desc())
        ).all()

        if not substitutes:
            return None

        sub = substitutes[0]
        sub_total_price = sub.selling_price_rupees * quantity
        sub_total_cost = sub.cost_price_rupees * quantity
        margin_percent = round(((sub_total_price - sub_total_cost) / sub_total_price) * 100.0, 2)

        return OfferCandidate(
            candidate_id=f"CAND-SUB-{uuid.uuid4().hex[:6].upper()}",
            strategy=AllowedStrategy.PRODUCT_SUBSTITUTE,
            explanation=f"Substituted with in-stock alternative {sub.name} (SKU: {sub.sku}) fitting budget cap Rs. {max_budget_rupees:,}.",
            items=[
                OfferItemDetail(
                    sku=sub.sku,
                    name=sub.name,
                    category=sub.category,
                    quantity=quantity,
                    unit_price_rupees=sub.selling_price_rupees,
                    total_price_rupees=sub_total_price,
                    unit_cost_rupees=sub.cost_price_rupees,
                    total_cost_rupees=sub_total_cost,
                    is_overstock=sub.is_overstock
                )
            ],
            total_price_rupees=sub_total_price,
            total_cost_rupees=sub_total_cost,
            margin_percent=margin_percent,
            discount_percent=0.0,
            overstock_items_count=0,
            overstock_ratio=0.0
        )
