"""Buyer-owned request drafts and a deliberately small public offer contract."""
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, text
from app.db.session import SessionLocal, get_db
from app.db.models.buyer_draft import BuyerDraft
from app.db.models.deal import Deal
from app.db.models.product import Product
from app.asc.catalog_search import find_products, specs_match
from app.asc.orchestrator import ASCOrchestrator
from app.domain.schemas import BuyerRequest, BuyerRequestItem
from app.domain.strategy_types import AllowedStrategy, OfferCandidate, OfferItemDetail
from app.llm.contracts import HardSpecifications, IntentIntelligence
from app.llm.providers import RuleBasedIntentProvider, GeminiFlashProvider, _json_object
from app.llm.service import IntentIntelligenceService
from app.api.commerce import _send_agent_message
from app.db.models.merchant_policy import MerchantPolicy
from app.db.models.agent_message import AgentMessage
from app.payments.base import MockPaymentProvider, PaymentProviderError, RazorpayPaymentProvider
from app.control_plane.control_plane_engine import ControlPlaneEngine
from app.audit.audit_service import AuditService

router = APIRouter(prefix="/api/buyer", tags=["Buyer"])


class Requirements(BaseModel):
    product_query: str | None = None
    quantity: int | None = Field(default=None, gt=0, le=100000)
    budget_mode: Literal["specified", "no_limit", "not_provided"] = "not_provided"
    max_budget_paise: int | None = Field(default=None, gt=0)
    hard_specs: HardSpecifications = Field(default_factory=HardSpecifications)
    preferences: list[str] = Field(default_factory=list)
    max_delivery_days: int | None = Field(default=None, gt=0)
    requested_discount_percent: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def budget(self):
        if self.budget_mode != "specified":
            self.max_budget_paise = None
        if self.budget_mode == "specified" and self.max_budget_paise is None:
            self.budget_mode = "not_provided"
        return self


class StartRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)


class UpdateRequest(BaseModel):
    requirements: Requirements


class Feedback(BaseModel):
    reason: str = Field(default="", max_length=1000)


class PaymentVerification(BaseModel):
    razorpay_payment_id: str = Field(min_length=4, max_length=100)
    razorpay_order_id: str = Field(min_length=4, max_length=100)
    razorpay_signature: str = Field(min_length=32, max_length=256)


def owner(request: Request):
    identity = request.cookies.get("asc_buyer")
    if not identity or not re.fullmatch(r"[a-f0-9]{32}", identity):
        raise HTTPException(401, "Start a buyer session first.")
    return identity


@router.post("/session")
def session(request: Request, response: Response):
    identity = request.cookies.get("asc_buyer")
    if not identity or not re.fullmatch(r"[a-f0-9]{32}", identity):
        identity = uuid.uuid4().hex
    response.set_cookie("asc_buyer", identity, httponly=True, samesite="strict", max_age=86400 * 30)
    return {"ready": True}


def owned(db, draft_id, identity):
    draft = db.get(BuyerDraft, draft_id)
    if not draft or draft.owner != identity:
        raise HTTPException(404, "Request not found.")
    return draft


def event(db, draft, state, label):
    draft.state = state
    draft.events = [*draft.events, {"state": state, "label": label, "timestamp": datetime.now(timezone.utc).isoformat()}]
    db.commit()


def extract(prompt):
    """One extraction; clarification subsequently updates structured fields only."""
    lower = prompt.lower()
    parsed = RuleBasedIntentProvider.inspect_required_fields(prompt)
    explicit = parsed["known_fields"]
    quantity = re.search(r"\b(?:buy|order|need|want|get)(?:\s+me)?\s+(\d+)\b", lower)
    if quantity:
        explicit["quantity"] = int(quantity[1])
    no_limit = bool(re.search(r"no\s+(?:limit\s+(?:in|on|to)\s+budget|budget\s+limit|limit|budget)|(?:don.t|do not)\s+have\s+(?:any\s+|a\s+)?budget|unlimited\s+budget|budget\s+(?:is\s+)?(?:unlimited|flexible)", lower))
    # Preserve brand/model identity. Generic queries map to catalog categories.
    query = explicit.get("product_query")
    match = re.search(r"\b(laptops?|notebooks?|monitors?|mice|mouse|keyboards?|chairs?)\b", lower)
    if match:
        category = {"mice": "mouse", "notebook": "laptop", "notebooks": "laptop"}.get(match[1], match[1].rstrip("s"))
        brands = [b for b in ("lenovo", "hp", "dell", "acer", "asus", "logitech", "samsung", "apple") if re.search(rf"\b{b}\b", lower)]
        query = " ".join([*brands, category])
        # Recognized named models must retain identity instead of becoming any laptop.
        for name in ("ideapad", "thinkpad", "probook", "inspiron", "ultrasharp"):
            if name in lower:
                query = " ".join([*brands, name])
                break
    with SessionLocal() as catalog_db:
        identities = catalog_db.scalars(select(Product)).all()
        named = [p for p in identities if p.model and len(p.model) >= 4 and re.search(r"[a-z]", p.model.lower()) and re.search(r"(?<!\w)" + re.escape(p.model.lower()) + r"(?!\w)", lower)]
        if named:
            selected = max(named, key=lambda p: len(p.model))
            query = " ".join([selected.brand or "", selected.model]).strip()
    specs = RuleBasedIntentProvider().analyze(prompt).hard_specs.model_dump()
    ryzen = re.search(r"\bryzen\s*([3579])\b", lower)
    if ryzen:
        specs["min_cpu_tier"] = f"Ryzen {ryzen[1]}"
    requested_discount = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:%|percent)\s*(?:discount|off)\b", lower)
    if not requested_discount:
        requested_discount = re.search(r"\b(?:discount|off)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:%|percent)\b", lower)
    data = {**explicit, "product_query": query, "hard_specs": specs,
            "budget_mode": "no_limit" if no_limit else "specified" if explicit.get("max_budget_paise") else "not_provided",
            "requested_discount_percent": float(requested_discount[1]) if requested_discount else None}
    provider = IntentIntelligenceService._configured_provider()
    metadata = {"provider": "deterministic", "model": None}
    if isinstance(provider, GeminiFlashProvider):
        try:
            extracted = _json_object(provider._generate(
                "Extract a procurement request. Use null for missing fields; never invent quantity, budget, or specifications. Preserve explicit brand/model. Product query must contain identity/category only, not RAM or CPU. Budget is TOTAL in integer Indian paise (1 lakh rupees = 10000000 paise). Explicit no budget limit means budget_mode=no_limit and null amount. Return JSON matching the schema.",
                prompt, True, Requirements.model_json_schema()))
            data = {**extracted, **{k: v for k, v in data.items() if v is not None and k not in {"hard_specs", "budget_mode"}}}
            # Explicit facts win; model may fill only what deterministic extraction missed.
            data["hard_specs"] = {**(extracted.get("hard_specs") or {}), **{k: v for k,v in specs.items() if v is not None}}
            if no_limit:
                data.update(budget_mode="no_limit", max_budget_paise=None)
            elif explicit.get("max_budget_paise"):
                data.update(budget_mode="specified", max_budget_paise=explicit["max_budget_paise"])
            if requested_discount:
                data["requested_discount_percent"] = float(requested_discount[1])
            metadata = {"provider": "gemini", "model": provider.model}
        except Exception:
            metadata = {"provider": "deterministic_fallback", "model": None}
    if no_limit:
        data.update(budget_mode="no_limit", max_budget_paise=None)
    quantity_words = r"one|two|three|four|five|six|seven|eight|nine|ten|twenty"
    if not explicit.get("quantity") and not re.search(rf"\b(?:{quantity_words})\b", lower) and not re.search(r"\bquantity\s*[:=]?\s*\d+", lower):
        data["quantity"] = None
    return Requirements.model_validate(data), metadata


def missing(requirements):
    result = []
    if not requirements.product_query: result.append("product_query")
    if not requirements.quantity: result.append("quantity")
    if requirements.budget_mode == "not_provided": result.append("budget")
    return result


def public_offer(offer, db):
    if not offer: return None
    items = []
    for item in offer["items"]:
        product = db.scalars(select(Product).where(Product.sku == item["sku"])).first()
        items.append({k: item[k] for k in ("sku", "name", "quantity", "unit_price_rupees", "total_price_rupees")})
        items[-1]["specifications"] = {k: getattr(product, k) for k in ("cpu_brand", "cpu_tier", "ram_gb", "storage_gb") if product and getattr(product, k) is not None}
    result = {"offer_id": offer["offer_id"], "total_price_paise": offer["total_price_paise"], "items": items}
    for key in ("requires_budget_approval", "original_budget_paise", "proposed_budget_paise", "value_included_paise"):
        if key in offer:
            result[key] = offer[key]
    return result


def process_negotiation(draft_id):
    """Build a fact-bound recovery bundle; never change the buyer mandate silently."""
    with SessionLocal() as db:
        draft = db.get(BuyerDraft, draft_id)
        if not draft or not draft.transaction_id:
            return
        try:
            req = Requirements.model_validate(draft.data["requirements"])
            deal = db.get(Deal, draft.transaction_id)
            event(db, draft, "NEGOTIATING", "Finding the best eligible offer")
            time.sleep(0.6)
            matches = find_products(db, req.product_query, req.hard_specs.model_dump(exclude_none=True))
            product = next((p for p in matches if p.stock_quantity >= req.quantity), None)
            mouse = db.scalars(select(Product).where(Product.sku == "ACC-DEMO-MOUSE", Product.is_active.is_(True))).first()
            if not product or not mouse or mouse.stock_quantity < req.quantity:
                draft.data = {**draft.data, "reply": "The merchant could not construct an eligible bundled offer for this request."}
                event(db, draft, "REPLIED", "Negotiation completed")
                return
            event(db, draft, "NEGOTIATING", "Comparing price and included value")
            time.sleep(0.6)
            total_price = product.selling_price_rupees * req.quantity
            total_cost = (product.cost_price_rupees + mouse.cost_price_rupees) * req.quantity
            list_value = (product.selling_price_rupees + mouse.selling_price_rupees) * req.quantity
            margin = round((total_price - total_cost) / total_price * 100, 2)
            value_discount = round((list_value - total_price) / list_value * 100, 2)
            candidate = OfferCandidate(
                candidate_id=f"CAND-NEG-{uuid.uuid4().hex[:6].upper()}",
                strategy=AllowedStrategy.BUNDLE_OVERSTOCK,
                explanation=f"Keep catalog pricing for {req.quantity}x {product.name} and include {req.quantity}x {mouse.name} from overstock at no charge.",
                items=[
                    OfferItemDetail(sku=product.sku, name=product.name, category=product.category, quantity=req.quantity,
                        unit_price_rupees=product.selling_price_rupees, total_price_rupees=total_price,
                        unit_cost_rupees=product.cost_price_rupees, total_cost_rupees=product.cost_price_rupees * req.quantity,
                        is_overstock=product.is_overstock),
                    OfferItemDetail(sku=mouse.sku, name=mouse.name, category=mouse.category, quantity=req.quantity,
                        unit_price_rupees=0, total_price_rupees=0, unit_cost_rupees=mouse.cost_price_rupees,
                        total_cost_rupees=mouse.cost_price_rupees * req.quantity, is_overstock=True),
                ],
                total_price_rupees=total_price, total_cost_rupees=total_cost, margin_percent=margin,
                discount_percent=value_discount, overstock_items_count=req.quantity,
                overstock_ratio=round(req.quantity / (req.quantity * 2), 2),
            )
            policy = db.scalars(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy", MerchantPolicy.is_active.is_(True))).first()
            proposed_budget = total_price
            passed, gates = ControlPlaneEngine().evaluate_candidate(
                db=db, transaction_id=deal.transaction_id, candidate=candidate,
                max_budget_rupees=proposed_budget, policy=policy,
                buyer_spec_requirements=req.hard_specs.model_dump(exclude_none=True),
                mandate={"max_amount": proposed_budget, "allowed_categories": ["LAPTOP", "ACCESSORY", "MONITOR"],
                    "expires_at": "2028-12-31T23:59:59Z", "transaction_id": deal.transaction_id},
            )
            formatted_candidate = {
                "strategy": candidate.strategy.value, "name": "Negotiated Overstock Bundle",
                "total_price_paise": total_price * 100, "total_cost_paise": total_cost * 100,
                "margin_percent": margin, "discount_percent": value_discount, "score": 0,
                "status": "WINNER" if passed else "REJECTED_POLICY",
                "note": candidate.explanation, "gate_results": [g.model_dump() for g in gates],
            }
            deal.candidates_json = [*(deal.candidates_json or []), formatted_candidate]
            deal.gate_results_json = [g.model_dump() for g in gates]
            if not passed:
                deal.status = "LOST"
                deal.current_offer_json = None
                reply = "The merchant explored a bundled recovery offer, but it did not pass the commercial controls."
            else:
                offer = {
                    "offer_id": candidate.candidate_id, "transaction_id": deal.transaction_id,
                    "strategy": candidate.strategy.value, "explanation": candidate.explanation,
                    "total_price_paise": total_price * 100, "margin_percent": margin,
                    "discount_percent": value_discount, "final_score": 0,
                    "items": [item.model_dump() for item in candidate.items],
                    "requires_budget_approval": True,
                    "original_budget_paise": req.max_budget_paise,
                    "proposed_budget_paise": proposed_budget * 100,
                    "value_included_paise": mouse.selling_price_rupees * req.quantity * 100,
                }
                deal.current_offer_json = offer
                deal.status = "RECOVERY_OFFER_SENT"
                deal.outcome_type = "NEGOTIATED_BUNDLE"
                reply = (
                    f"This is the best eligible offer after negotiation: {req.quantity} × {product.name} for "
                    f"₹{total_price:,.2f}, plus {req.quantity} × {mouse.name} included at no charge. "
                    f"It is ₹{(total_price * 100 - (req.max_budget_paise or 0)) / 100:,.2f} above your original budget, "
                    "so you must explicitly approve the revised amount."
                )
            deal.merchant_response_json = {
                "response_type": "OFFER_AVAILABLE" if passed else "POLICY_REJECTED",
                "message": reply, "inventory_available": True,
                "requested_budget_paise": req.max_budget_paise, "policy_reasons": [],
            }
            draft.data = {**draft.data, "reply": reply}
            db.add(AgentMessage(transaction_id=deal.transaction_id, sender="BUYER_AGENT", recipient="MERCHANT_AGENT",
                message_type="NEGOTIATION_REQUESTED", content="The buyer asked the agents to find a better eligible arrangement.", metadata_json={}))
            db.add(AgentMessage(transaction_id=deal.transaction_id, sender="MERCHANT_AGENT", recipient="BUYER_AGENT",
                message_type="NEGOTIATED_PROPOSAL" if passed else "NEGOTIATION_FAILED", content=reply, metadata_json={}))
            event(db, draft, "REPLIED", "Best negotiated offer received")
        except Exception:
            db.rollback()
            draft = db.get(BuyerDraft, draft_id)
            if draft:
                draft.data = {**draft.data, "error": "Negotiation was interrupted. Your original request is unchanged."}
                event(db, draft, "ERROR", "Negotiation interrupted")
            import logging
            logging.getLogger(__name__).exception("Buyer negotiation failed: %s", draft_id)


def public(draft, db):
    req = Requirements.model_validate(draft.data.get("requirements", {}))
    deal = db.get(Deal, draft.transaction_id) if draft.transaction_id else None
    return {"id": draft.id, "prompt": draft.prompt, "state": draft.state,
        "requirements": req.model_dump(mode="json"), "missing_fields": missing(req) if draft.state == "NEEDS_DETAILS" else [],
        "events": draft.events, "transaction_id": draft.transaction_id,
        "reply": draft.data.get("reply"), "error": draft.data.get("error"),
        "offer": public_offer(deal.current_offer_json, db) if deal else None}


def process(draft_id, parse=True):
    with SessionLocal() as db:
        draft = db.get(BuyerDraft, draft_id)
        if not draft: return
        try:
            if parse:
                req, metadata = extract(draft.prompt)
                draft.data = {"requirements": req.model_dump(mode="json"), "intelligence": metadata}
                db.commit()
            else:
                req = Requirements.model_validate(draft.data["requirements"])
                metadata = draft.data.get("intelligence", {})
            if missing(req):
                event(db, draft, "NEEDS_DETAILS", "A few details are needed")
                return
            event(db, draft, "SENT", "Request sent to merchant")
            event(db, draft, "WAITING", "Waiting for merchant response")
            matches = find_products(db, req.product_query, req.hard_specs.model_dump(exclude_none=True))
            strategies = [AllowedStrategy.DIRECT_MATCH, AllowedStrategy.VOLUME_DISCOUNT]
            merchant_metadata = {"provider": "deterministic"}
            merchant = IntentIntelligenceService._configured_provider()
            if isinstance(merchant, GeminiFlashProvider):
                try:
                    decision = _json_object(merchant._generate(
                        "You represent the merchant. Recommend the commercial approach to satisfy the buyer while preserving merchant profit. Return only strategy names from the supplied schema. Do not change quantities, prices, specifications, or budget. Deterministic code evaluates all offers and enforces policies.",
                        json.dumps({"request": req.model_dump(mode="json"), "matching_products": [{"sku": p.sku, "price_rupees": p.selling_price_rupees, "stock": p.stock_quantity} for p in matches]}),
                        True, {"type":"object", "properties":{"strategies":{"type":"array", "items":{"type":"string", "enum":["DIRECT_MATCH","VOLUME_DISCOUNT"]}}}, "required":["strategies"]}))
                    strategies = list(dict.fromkeys([*strategies, *[AllowedStrategy(s) for s in decision["strategies"]]]))
                    merchant_metadata = {"provider": "gemini", "model": merchant.model}
                except Exception:
                    merchant_metadata = {"provider": "deterministic_fallback"}
            # Open-budget discovery uses actual catalog values as an evaluation
            # ceiling. It is never stored or presented as a buyer spending mandate.
            evaluation_cap = req.max_budget_paise if req.budget_mode == "specified" else max((p.selling_price_rupees * req.quantity * 100 for p in matches), default=100)
            intelligence = IntentIntelligence(
                product_query=req.product_query, quantity=req.quantity, max_budget_paise=evaluation_cap,
                hard_specs=req.hard_specs, max_delivery_days=req.max_delivery_days, preferences=req.preferences,
                recommended_strategies=strategies,
                provider=metadata.get("provider", "deterministic"), model=metadata.get("model"))
            request = BuyerRequest(request_id=draft.id, items=[BuyerRequestItem(product_query=req.product_query, quantity=req.quantity)], max_budget_paise=evaluation_cap, max_delivery_days=req.max_delivery_days, preferences=req.preferences)
            request.requested_discount_percent = req.requested_discount_percent
            result = ASCOrchestrator().process_purchase_request(request, intelligence)
            offer = result.get("offer")
            requested_rejected = req.requested_discount_percent is not None and any(
                c.get("strategy") == "BUYER_REQUESTED_DISCOUNT" and c.get("status") == "REJECTED_POLICY"
                for c in result.get("candidates", [])
            )
            if offer:
                names = ", ".join(f"{i['quantity']} × {i['name']}" for i in offer["items"])
                prefix = f"We cannot approve a {req.requested_discount_percent:g}% discount. " if requested_rejected else ""
                reply = f"{prefix}We can supply {names} for ₹{offer['total_price_paise'] / 100:,.2f}. Review the proposal to proceed to checkout."
            elif not matches:
                reply = "We do not currently have a product matching these requirements. Would you like to change the requested specifications or product?"
            elif not any(p.stock_quantity >= req.quantity for p in matches):
                reply = "We have matching products, but cannot supply the full requested quantity right now. Would you like to request fewer units?"
            else:
                reply = "We have matching products, but cannot offer the requested quantity within your budget. You can revise the quantity, budget, or specifications."
            intelligence_json = {**intelligence.model_dump(mode="json"), "budget_mode": req.budget_mode, "max_budget_paise": req.max_budget_paise, "merchant_intelligence": merchant_metadata}
            deal = Deal(transaction_id=result["transaction_id"], title=f"{req.product_query} purchase", prompt=draft.prompt, product_query=req.product_query, quantity=req.quantity,
                max_budget_paise=req.max_budget_paise, status="WAITING_FOR_BUYER" if offer else "LOST", intelligence_json=intelligence_json,
                outcome_type=result.get("outcome_type"), initial_offer_json=offer, current_offer_json=offer,
                candidates_json=result.get("candidates", []), gate_results_json=result.get("gate_results", []),
                merchant_response_json={"response_type": "OFFER_AVAILABLE" if offer else "NO_FEASIBLE_OFFER", "message": reply, "inventory_available": bool(matches), "requested_budget_paise": req.max_budget_paise, "policy_reasons": []})
            db.add(deal)
            db.commit()
            _send_agent_message(db, deal.transaction_id, "BUYER_AGENT", "MERCHANT_AGENT", "PURCHASE_REQUEST", f"Request: {req.quantity} × {req.product_query}.")
            _send_agent_message(db, deal.transaction_id, "MERCHANT_AGENT", "BUYER_AGENT", "PROPOSAL" if offer else "UNABLE_TO_OFFER", reply)
            draft.transaction_id = deal.transaction_id
            draft.data = {**draft.data, "reply": reply}
            event(db, draft, "REPLIED", "Merchant reply received")
        except Exception:
            db.rollback()
            draft = db.get(BuyerDraft, draft_id)
            draft.data = {**draft.data, "error": "We could not complete this request. Please retry; your requirements have been saved."}
            event(db, draft, "ERROR", "Request interrupted")
            import logging
            logging.getLogger(__name__).exception("Buyer request failed: %s", draft_id)


@router.post("/requests", status_code=202)
def start(payload: StartRequest, tasks: BackgroundTasks, identity=Depends(owner), db=Depends(get_db)):
    draft = BuyerDraft(id=uuid.uuid4().hex, owner=identity, prompt=payload.prompt, state="PREPARING", data={}, events=[])
    db.add(draft)
    event(db, draft, "PREPARING", "Preparing your request")
    tasks.add_task(process, draft.id)
    return public(draft, db)


@router.get("/requests")
def listing(identity=Depends(owner), db=Depends(get_db)):
    return {"requests": [public(d, db) for d in db.scalars(select(BuyerDraft).where(BuyerDraft.owner == identity)).all()]}


@router.get("/requests/{draft_id}")
def get(draft_id: str, identity=Depends(owner), db=Depends(get_db)):
    return public(owned(db, draft_id, identity), db)


@router.patch("/requests/{draft_id}", status_code=202)
def update(draft_id: str, payload: UpdateRequest, tasks: BackgroundTasks, identity=Depends(owner), db=Depends(get_db)):
    draft = owned(db, draft_id, identity)
    if draft.state in {"PREPARING", "SENT", "WAITING", "NEGOTIATING", "COMPLETED"}:
        raise HTTPException(409, "This request cannot be revised in its current state.")
    if draft.transaction_id:
        previous = db.get(Deal, draft.transaction_id)
        if previous and previous.status != "COMPLETED":
            previous.status = "LOST"
            previous.current_offer_json = None
            previous.rejection_reason = "Superseded by the buyer's revised request."
    draft.data = {"requirements": payload.requirements.model_dump(mode="json"), "intelligence": draft.data.get("intelligence", {})}
    draft.transaction_id = None
    event(db, draft, "PREPARING", "Preparing your revised request")
    tasks.add_task(process, draft.id, False)
    return public(draft, db)


@router.post("/requests/{draft_id}/decline")
def decline(draft_id: str, payload: Feedback, identity=Depends(owner), db=Depends(get_db)):
    draft = owned(db, draft_id, identity)
    if draft.state != "REPLIED": raise HTTPException(409, "There is no reply to decline.")
    if draft.transaction_id:
        deal = db.get(Deal, draft.transaction_id)
        deal.status = "LOST"
        deal.rejection_reason = payload.reason or None
        deal.current_offer_json = None
        db.commit()
        _send_agent_message(db, deal.transaction_id, "BUYER_AGENT", "MERCHANT_AGENT", "OFFER_REJECTED", payload.reason or "The buyer declined the offer.")
    event(db, draft, "DECLINED", "Offer declined")
    return public(draft, db)


@router.post("/requests/{draft_id}/negotiate", status_code=202)
def negotiate(draft_id: str, tasks: BackgroundTasks, identity=Depends(owner), db=Depends(get_db)):
    draft = owned(db, draft_id, identity)
    if draft.state != "REPLIED" or not draft.transaction_id:
        raise HTTPException(409, "This request is not ready for negotiation.")
    deal = db.get(Deal, draft.transaction_id)
    if not deal or deal.current_offer_json:
        raise HTTPException(409, "Negotiate is available when the merchant could not provide an initial offer.")
    event(db, draft, "NEGOTIATING", "Negotiating with the merchant")
    tasks.add_task(process_negotiation, draft.id)
    return public(draft, db)


def _validate_checkout(db, draft, *, decrement_stock=False):
    """Re-check every commercial invariant; never trust browser checkout fields."""
    deal = db.get(Deal, draft.transaction_id)
    offer = deal.current_offer_json if deal else None
    if not offer or deal.status not in {"WAITING_FOR_BUYER", "RECOVERY_OFFER_SENT"}:
        raise HTTPException(409, "This proposal is no longer available.")
    req = Requirements.model_validate(draft.data["requirements"])
    if offer.get("requires_budget_approval"):
        proposed = offer.get("proposed_budget_paise")
        if not proposed or offer["total_price_paise"] != proposed:
            raise HTTPException(409, "The revised budget could not be verified.")
        req.budget_mode = "specified"
        req.max_budget_paise = proposed
        draft.data = {**draft.data, "requirements": req.model_dump(mode="json")}
    policy = db.scalars(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy", MerchantPolicy.is_active.is_(True))).first()
    if not policy: raise HTTPException(409, "This merchant is not currently accepting purchases.")
    total = offer["total_price_paise"]
    if req.budget_mode == "specified" and total > req.max_budget_paise:
        raise HTTPException(409, "The proposal exceeds your budget. Please request a revision.")
    total_cost = 0
    catalog = 0
    quantities = {}
    for item in offer["items"]:
        quantities[item["sku"]] = quantities.get(item["sku"], 0) + item["quantity"]
    for sku, quantity in quantities.items():
        product = db.scalars(select(Product).where(Product.sku == sku)).first()
        if not product or not product.is_active or product.stock_quantity < quantity or not specs_match(product, req.hard_specs.model_dump(exclude_none=True)):
            raise HTTPException(409, "Availability has changed. Please request a new proposal.")
        total_cost += product.cost_price_rupees * quantity * 100
        catalog += product.selling_price_rupees * quantity * 100
        if decrement_stock:
            product.stock_quantity -= quantity
    margin = (total - total_cost) / total * 100
    discount = (catalog - total) / catalog * 100
    if margin + 1e-7 < policy.min_margin_percent or discount - 1e-7 > policy.max_discount_percent:
        raise HTTPException(409, "The merchant can no longer honor this proposal. Please request an updated offer.")
    return deal, offer, total


def _checkout_payload(provider, order, draft):
    return {
        "key_id": provider.key_id,
        "order_id": order["id"],
        "amount": int(order["amount"]),
        "currency": order.get("currency", "INR"),
        "name": "ASC Commerce",
        "description": f"Purchase request {draft.id[:10]}",
        "demo": order.get("provider") == "RAZORPAY_DEMO",
    }


@router.post("/requests/{draft_id}/checkout")
def checkout(draft_id: str, identity=Depends(owner), db=Depends(get_db)):
    """Create a Razorpay Order. This does not fulfil or complete the ASC deal."""
    db.execute(text("BEGIN IMMEDIATE"))
    draft = owned(db, draft_id, identity)
    if draft.state == "PAYMENT_PENDING":
        saved = draft.data.get("checkout") or {}
        if saved.get("provider") in {"RAZORPAY", "RAZORPAY_DEMO"} and saved.get("id"):
            return {"purchase": public(draft, db), "checkout": _checkout_payload(RazorpayPaymentProvider(), saved, draft)}
    if draft.state != "REPLIED" or not draft.transaction_id:
        raise HTTPException(409, "There is no proposal ready for payment.")
    _, _, total = _validate_checkout(db, draft)
    provider = RazorpayPaymentProvider()
    if not provider.key_id or not provider.key_secret:
        created = MockPaymentProvider().create_order(total, "INR", draft.id)
        order = {"id": created["id"], "amount": total, "currency": "INR", "status": "created", "provider": "RAZORPAY_DEMO"}
        draft.data = {**draft.data, "checkout": order}
        event(db, draft, "PAYMENT_PENDING", "Secure demo payment opened")
        return {"purchase": public(draft, db), "checkout": _checkout_payload(provider, order, draft)}
    try:
        created = provider.create_order(total, "INR", f"asc-{draft.id}")
    except PaymentProviderError as exc:
        db.rollback()
        raise HTTPException(503, str(exc)) from exc
    order = {"id": created["id"], "amount": int(created["amount"]), "currency": created.get("currency", "INR"),
             "status": created.get("status", "created"), "provider": "RAZORPAY"}
    draft.data = {**draft.data, "checkout": order}
    event(db, draft, "PAYMENT_PENDING", "Secure payment opened")
    return {"purchase": public(draft, db), "checkout": _checkout_payload(provider, order, draft)}


@router.post("/requests/{draft_id}/payment/verify")
def verify_payment(draft_id: str, payload: PaymentVerification, identity=Depends(owner), db=Depends(get_db)):
    draft = owned(db, draft_id, identity)
    saved = draft.data.get("checkout") or {}
    if draft.state == "COMPLETED" and saved.get("payment_id") == payload.razorpay_payment_id:
        return public(draft, db)
    if draft.state != "PAYMENT_PENDING" or saved.get("provider") != "RAZORPAY":
        raise HTTPException(409, "This purchase is not awaiting payment verification.")
    server_order_id = saved.get("id")
    if not server_order_id or payload.razorpay_order_id != server_order_id:
        raise HTTPException(400, "Payment order verification failed. No purchase was completed.")
    # Do not hold a database transaction open while calling Razorpay.
    db.rollback()
    provider = RazorpayPaymentProvider()
    try:
        signature_valid = provider.verify_payment(payload.razorpay_payment_id, server_order_id, payload.razorpay_signature)
        payment = provider.fetch_payment(payload.razorpay_payment_id) if signature_valid else {}
    except PaymentProviderError as exc:
        raise HTTPException(503, str(exc)) from exc
    if not signature_valid:
        raise HTTPException(400, "Payment signature verification failed. No purchase was completed.")
    if (payment.get("order_id") != server_order_id or int(payment.get("amount", -1)) != int(saved["amount"])
            or payment.get("currency") != saved["currency"] or payment.get("status") != "captured"):
        raise HTTPException(409, "Payment is not captured or does not match this purchase. No order was fulfilled.")

    # Signature and captured status are valid. Lock stock and revalidate once more before fulfilment.
    db.execute(text("BEGIN IMMEDIATE"))
    draft = owned(db, draft_id, identity)
    current = draft.data.get("checkout") or {}
    if draft.state == "COMPLETED" and current.get("payment_id") == payload.razorpay_payment_id:
        return public(draft, db)
    if draft.state != "PAYMENT_PENDING" or current.get("id") != server_order_id:
        raise HTTPException(409, "The purchase changed while payment was being verified.")
    deal, offer, _ = _validate_checkout(db, draft, decrement_stock=True)
    recovered_purchase = deal.status == "RECOVERY_OFFER_SENT" or bool(offer.get("requires_budget_approval"))
    deal.status = "COMPLETED"
    deal.recovered = recovered_purchase
    deal.outcome_type = "RECOVERED" if recovered_purchase else "DIRECT_MATCH"
    deal.completed_at = datetime.now(timezone.utc)
    deal.updated_at = deal.completed_at
    draft.data = {**draft.data, "checkout": {**current, "status": "captured", "payment_id": payload.razorpay_payment_id}}
    db.add(AgentMessage(
        transaction_id=deal.transaction_id,
        sender="BUYER_AGENT", recipient="MERCHANT_AGENT",
        message_type="OFFER_ACCEPTED",
        content="The buyer approved the offer and completed verified Razorpay checkout.",
        metadata_json={"payment_provider": "RAZORPAY", "payment_id": payload.razorpay_payment_id},
    ))
    event(db, draft, "COMPLETED", "Payment verified and purchase completed")
    return public(draft, db)


@router.post("/requests/{draft_id}/payment/demo")
def complete_demo_payment(draft_id: str, identity=Depends(owner), db=Depends(get_db)):
    """Explicit simulation for demos when Razorpay credentials are unavailable."""
    db.execute(text("BEGIN IMMEDIATE"))
    draft = owned(db, draft_id, identity)
    saved = draft.data.get("checkout") or {}
    if draft.state != "PAYMENT_PENDING" or saved.get("provider") != "RAZORPAY_DEMO":
        raise HTTPException(409, "This request is not awaiting a demo payment.")
    deal, offer, _ = _validate_checkout(db, draft, decrement_stock=True)
    recovered_purchase = deal.status == "RECOVERY_OFFER_SENT" or bool(offer.get("requires_budget_approval"))
    deal.status = "COMPLETED"
    deal.recovered = recovered_purchase
    deal.outcome_type = "RECOVERED" if recovered_purchase else "DIRECT_MATCH"
    deal.completed_at = datetime.now(timezone.utc)
    deal.updated_at = deal.completed_at
    draft.data = {**draft.data, "checkout": {**saved, "status": "captured", "payment_id": f"pay_demo_{uuid.uuid4().hex[:10]}"}}
    db.add(AgentMessage(transaction_id=deal.transaction_id, sender="BUYER_AGENT", recipient="MERCHANT_AGENT",
        message_type="OFFER_ACCEPTED", content="The buyer completed the Razorpay checkout simulation.",
        metadata_json={"payment_provider": "RAZORPAY_DEMO", "simulated": True}))
    AuditService.log_event(db, deal.transaction_id, "COMMERCE_CONTROL", "PAYMENT_CONFIRMED", "PASS",
        "Buyer payment confirmed; deal revenue and recovery outcome recorded.",
        {"amount_paise": offer["total_price_paise"], "recovered": recovered_purchase, "provider": "RAZORPAY_DEMO"})
    event(db, draft, "COMPLETED", "Demo payment completed securely")
    return public(draft, db)


@router.post("/requests/{draft_id}/payment/cancel")
def cancel_payment(draft_id: str, identity=Depends(owner), db=Depends(get_db)):
    draft = owned(db, draft_id, identity)
    if draft.state == "PAYMENT_PENDING":
        draft.data = {**draft.data, "checkout": None}
        event(db, draft, "REPLIED", "Payment cancelled — proposal remains available")
    return public(draft, db)


@router.post("/requests/{draft_id}/accept", status_code=410)
def accept(draft_id: str, identity=Depends(owner), db=Depends(get_db)):
    owned(db, draft_id, identity)
    raise HTTPException(410, "Demo checkout was removed. Use secure Razorpay checkout.")
