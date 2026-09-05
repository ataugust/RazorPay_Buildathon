"""Synchronized deal, catalog, policy, and merchant analytics APIs."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.asc.candidate_generators import (
    OverstockBundleGenerator,
    ProductSubstituteGenerator,
    RecoveryDiscountGenerator,
)
from app.asc.intent_parser import IntentParser
from app.asc.orchestrator import ASCOrchestrator
from app.asc.scoring_engine import DeterministicScoringEngine
from app.audit.audit_service import AuditService
from app.control_plane.control_plane_engine import ControlPlaneEngine
from app.db.models.audit_event import AuditEvent
from app.db.models.agent_message import AgentMessage
from app.db.models.deal import Deal
from app.db.models.merchant_policy import MerchantPolicy
from app.db.models.product import Product
from app.db.session import get_db
from app.payments.base import MockPaymentProvider
from app.llm.service import AgentLanguageService

router = APIRouter(prefix="/api", tags=["Commerce Workspace"])
orchestrator = ASCOrchestrator()
control_plane = ControlPlaneEngine()
payments = MockPaymentProvider()
agent_language = AgentLanguageService()


class DealCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)


class RejectPayload(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)


class PolicyUpdate(BaseModel):
    min_margin_percent: Optional[float] = Field(default=None, ge=0, le=100)
    max_discount_percent: Optional[float] = Field(default=None, ge=0, le=100)
    allow_bundles: Optional[bool] = None
    allow_substitutions: Optional[bool] = None
    weight_margin: Optional[float] = Field(default=None, ge=0)
    weight_revenue: Optional[float] = Field(default=None, ge=0)
    weight_overstock: Optional[float] = Field(default=None, ge=0)
    weight_discount_penalty: Optional[float] = Field(default=None, ge=0)


def _event(event: AuditEvent) -> Dict[str, Any]:
    return {
        "id": event.id,
        "timestamp": _iso(event.timestamp),
        "transaction_id": event.transaction_id,
        "component": event.component,
        "event_type": event.event_type,
        "status": event.status,
        "message": event.message,
        "metadata": event.metadata_json or {},
    }


def _deal(deal: Deal, db: Session, include_events: bool = True) -> Dict[str, Any]:
    payload = {
        "transaction_id": deal.transaction_id,
        "title": deal.title,
        "prompt": deal.prompt,
        "product_query": deal.product_query,
        "quantity": deal.quantity,
        "max_budget_paise": deal.max_budget_paise,
        "status": deal.status,
        "outcome_type": deal.outcome_type,
        "recovered": deal.recovered,
        "rejection_reason": deal.rejection_reason,
        "merchant_response": deal.merchant_response_json,
        "intelligence": deal.intelligence_json,
        "initial_offer": deal.initial_offer_json,
        "current_offer": deal.current_offer_json,
        "candidates": deal.candidates_json or [],
        "gate_results": deal.gate_results_json or [],
        "created_at": _iso(deal.created_at),
        "updated_at": _iso(deal.updated_at),
        "completed_at": _iso(deal.completed_at) if deal.completed_at else None,
    }
    if include_events:
        payload["events"] = [
            _event(event)
            for event in AuditService.get_transaction_audit_trail(db, deal.transaction_id)
        ]
        payload["messages"] = [
            _agent_message(message)
            for message in db.scalars(
                select(AgentMessage)
                .where(AgentMessage.transaction_id == deal.transaction_id)
                .order_by(AgentMessage.created_at, AgentMessage.id)
            ).all()
        ]
    return payload


def _agent_message(message: AgentMessage) -> Dict[str, Any]:
    return {
        "id": message.id,
        "transaction_id": message.transaction_id,
        "sender": message.sender,
        "recipient": message.recipient,
        "message_type": message.message_type,
        "content": message.content,
        "reason_code": message.reason_code,
        "metadata": message.metadata_json or {},
        "timestamp": _iso(message.created_at),
    }


def _send_agent_message(
    db: Session,
    transaction_id: str,
    sender: str,
    recipient: str,
    message_type: str,
    content: str,
    reason_code: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    db.add(AgentMessage(
        transaction_id=transaction_id,
        sender=sender,
        recipient=recipient,
        message_type=message_type,
        content=content,
        reason_code=reason_code,
        metadata_json=metadata or {},
    ))
    db.commit()


def _rupees(paise: int) -> str:
    return f"Rs. {paise // 100:,}"


def _merchant_response(
    result: Dict[str, Any],
    product: Optional[Product],
    quantity: int,
    budget_paise: int,
) -> Dict[str, Any]:
    offer = result.get("offer")
    catalog_total = result.get("catalog_total_paise")
    inventory_available = bool(product and product.is_active and product.stock_quantity >= quantity)
    candidates = result.get("candidates") or []
    selected_candidate = next(
        (candidate for candidate in candidates if candidate.get("status") == "WINNER"),
        candidates[0] if candidates else None,
    )
    closest_price = selected_candidate.get("total_price_paise") if selected_candidate else catalog_total
    failed_gates = [gate for gate in (result.get("gate_results") or []) if gate.get("status") == "FAIL"]
    friendly_reasons = {
        "MARGIN_GATE": "The attempted discount would fall below the merchant's minimum sustainable margin.",
        "BUDGET_GATE": "The evaluated offer still exceeds your maximum budget.",
        "INVENTORY_GATE": "The requested quantity is not currently available.",
        "DISCOUNT_GATE": "The required discount exceeds the merchant's allowed discount limit.",
        "SPECIFICATION_GATE": "The available product does not meet all required specifications.",
        "MANDATE_GATE": "The evaluated offer exceeds the Buyer Agent's authorized spending limit.",
    }
    policy_reasons = [
        friendly_reasons.get(gate.get("gate"), gate.get("reason"))
        for gate in failed_gates if friendly_reasons.get(gate.get("gate"), gate.get("reason"))
    ]
    discount_attempted = any(candidate.get("strategy") == "VOLUME_DISCOUNT" for candidate in candidates)

    if offer:
        response_type = "OFFER_AVAILABLE"
        message = f"I can provide {quantity} × {offer['items'][0]['name']} for {_rupees(offer['total_price_paise'])}."
        suggested_actions = ["REVIEW_OFFER"]
    elif not product or not inventory_available:
        response_type = "NO_INVENTORY"
        message = (
            f"I cannot provide {quantity} units because the requested product is not available in sufficient inventory."
            if product else
            "I could not find the requested product in the merchant catalog."
        )
        suggested_actions = ["REDUCE_QUANTITY", "ALLOW_ALTERNATIVES", "MODIFY_REQUIREMENTS"]
    elif catalog_total and catalog_total > budget_paise:
        response_type = "BUDGET_TOO_LOW"
        message = (
            f"Matching inventory is available, but I cannot provide a policy-compliant offer within your {_rupees(budget_paise)} budget. "
            f"The catalog total is {_rupees(catalog_total)}"
            + (f" and the closest evaluated offer is {_rupees(closest_price)}" if closest_price else "")
            + ". Increase your budget, reduce the quantity, or allow lower-cost alternatives."
        )
        suggested_actions = ["INCREASE_BUDGET", "REDUCE_QUANTITY", "ALLOW_ALTERNATIVES"]
    elif failed_gates:
        response_type = "POLICY_REJECTED"
        message = "Inventory is available, but every evaluated offer failed the merchant's commercial controls."
        suggested_actions = ["MODIFY_REQUIREMENTS", "ALLOW_ALTERNATIVES"]
    else:
        response_type = "NO_FEASIBLE_OFFER"
        message = "I checked the available inventory and could not construct an eligible offer for this request."
        suggested_actions = ["MODIFY_REQUIREMENTS", "ALLOW_ALTERNATIVES"]

    response = {
        "response_type": response_type,
        "message": message,
        "inventory_available": inventory_available,
        "requested_budget_paise": budget_paise,
        "catalog_total_paise": catalog_total,
        "closest_offer_price_paise": closest_price,
        "budget_gap_paise": max(0, (closest_price or catalog_total or 0) - budget_paise),
        "discount_attempted": discount_attempted,
        "policy_reasons": policy_reasons,
        "suggested_actions": suggested_actions,
    }
    generated_message, language_provider, language_model = agent_language.compose_merchant_reply(response)
    response["message"] = generated_message
    response["language_provider"] = language_provider
    response["language_model"] = language_model
    return response


def _publish_merchant_response(
    db: Session,
    deal: Deal,
    response: Dict[str, Any],
    event_type: str = "MERCHANT_RESPONSE_SENT",
) -> None:
    if "language_provider" not in response:
        generated_message, language_provider, language_model = agent_language.compose_merchant_reply(response)
        response["message"] = generated_message
        response["language_provider"] = language_provider
        response["language_model"] = language_model
    deal.merchant_response_json = response
    deal.updated_at = datetime.now(timezone.utc)
    db.commit()
    AuditService.log_event(
        db, deal.transaction_id, "MERCHANT_AGENT", event_type,
        "INFO" if response["response_type"] == "OFFER_AVAILABLE" else "WARN",
        response["message"], {"reason_code": response["response_type"]},
    )
    _send_agent_message(
        db, deal.transaction_id, "MERCHANT_AGENT", "BUYER_AGENT",
        "PROPOSAL" if response["response_type"] == "OFFER_AVAILABLE" else "UNABLE_TO_OFFER",
        response["message"], response["response_type"], response,
    )


def _iso(value: datetime) -> str:
    """SQLite returns naive UTC datetimes; expose an explicit UTC API contract."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _policy(policy: MerchantPolicy) -> Dict[str, Any]:
    return {
        "id": policy.id,
        "policy_name": policy.policy_name,
        "min_margin_percent": policy.min_margin_percent,
        "max_discount_percent": policy.max_discount_percent,
        "allow_bundles": policy.allow_bundles,
        "allow_substitutions": policy.allow_substitutions,
        "weight_margin": policy.weight_margin,
        "weight_revenue": policy.weight_revenue,
        "weight_overstock": policy.weight_overstock,
        "weight_discount_penalty": policy.weight_discount_penalty,
        "is_active": policy.is_active,
        "updated_at": policy.updated_at.isoformat(),
    }


@router.post("/deals")
def create_deal(payload: DealCreate, db: Session = Depends(get_db)):
    inspection = agent_language.inspect_required_fields(payload.prompt)
    if inspection["missing_fields"]:
        questions = {
            "product_query": {
                "field": "product_query",
                "label": "Product",
                "question": "What product would you like to buy?",
                "input_type": "text",
            },
            "quantity": {
                "field": "quantity",
                "label": "Quantity",
                "question": "How many units do you need?",
                "input_type": "number",
            },
            "max_budget_paise": {
                "field": "max_budget_paise",
                "label": "Maximum total budget",
                "question": "What is the maximum total budget in rupees?",
                "input_type": "money",
            },
        }
        return {
            "requires_clarification": True,
            "original_prompt": payload.prompt,
            "known_fields": inspection["known_fields"],
            "missing_fields": inspection["missing_fields"],
            "questions": [questions[field] for field in inspection["missing_fields"]],
        }
    buyer_request, intelligence = IntentParser.parse_with_intelligence(payload.prompt)
    result = orchestrator.process_purchase_request(buyer_request, intelligence)
    item = buyer_request.items[0]
    product = db.scalars(
        select(Product).where(Product.name.contains(item.product_query))
    ).first()
    merchant_response = _merchant_response(
        result, product, item.quantity, buyer_request.max_budget_paise
    )
    deal = Deal(
        transaction_id=result["transaction_id"],
        title=f"{item.product_query} purchase",
        prompt=payload.prompt,
        product_query=item.product_query,
        quantity=item.quantity,
        max_budget_paise=buyer_request.max_budget_paise,
        status="WAITING_FOR_BUYER" if result.get("offer") else "LOST",
        outcome_type=result.get("outcome_type"),
        merchant_response_json=merchant_response,
        intelligence_json=intelligence.model_dump(mode="json"),
        initial_offer_json=result.get("offer"),
        current_offer_json=result.get("offer"),
        candidates_json=result.get("candidates", []),
        gate_results_json=result.get("gate_results", []),
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    _send_agent_message(
        db, deal.transaction_id, "BUYER_AGENT", "MERCHANT_AGENT", "PURCHASE_REQUEST",
        f"Request for {deal.quantity} × {deal.product_query} with a maximum budget of {_rupees(deal.max_budget_paise)}.",
        metadata={"quantity": deal.quantity, "max_budget_paise": deal.max_budget_paise},
    )
    response_event = "PROPOSAL_SENT" if deal.current_offer_json else "MERCHANT_RESPONSE_SENT"
    AuditService.log_event(
        db, deal.transaction_id, "MERCHANT_AGENT", response_event,
        "INFO" if deal.current_offer_json else "WARN",
        "Merchant proposal sent to the Buyer Workspace."
        if deal.current_offer_json else merchant_response["message"],
        {"offer_id": (deal.current_offer_json or {}).get("offer_id"), "reason_code": merchant_response["response_type"]},
    )
    _send_agent_message(
        db, deal.transaction_id, "MERCHANT_AGENT", "BUYER_AGENT",
        "PROPOSAL" if deal.current_offer_json else "UNABLE_TO_OFFER",
        merchant_response["message"], merchant_response["response_type"], merchant_response,
    )
    db.refresh(deal)
    return _deal(deal, db)


@router.get("/deals")
def list_deals(db: Session = Depends(get_db)):
    deals = db.scalars(select(Deal).order_by(Deal.created_at.desc())).all()
    return {"deals": [_deal(deal, db, include_events=False) for deal in deals]}


@router.get("/deals/{transaction_id}")
def get_deal(transaction_id: str, db: Session = Depends(get_db)):
    deal = db.get(Deal, transaction_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _deal(deal, db)


@router.get("/deals/{transaction_id}/messages")
def get_deal_messages(transaction_id: str, db: Session = Depends(get_db)):
    if not db.get(Deal, transaction_id):
        raise HTTPException(status_code=404, detail="Deal not found")
    messages = db.scalars(
        select(AgentMessage)
        .where(AgentMessage.transaction_id == transaction_id)
        .order_by(AgentMessage.created_at, AgentMessage.id)
    ).all()
    return {"messages": [_agent_message(message) for message in messages]}


@router.post("/deals/{transaction_id}/reject")
def reject_deal(
    transaction_id: str,
    payload: Optional[RejectPayload] = None,
    db: Session = Depends(get_db),
):
    deal = db.get(Deal, transaction_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status == "RECOVERY_OFFER_SENT":
        deal.status = "LOST"
        deal.updated_at = datetime.now(timezone.utc)
        AuditService.log_event(db, transaction_id, "BUYER_AGENT", "RECOVERY_DECLINED", "WARN", "Buyer declined the recovery offer.")
        db.commit()
        _send_agent_message(
            db, transaction_id, "BUYER_AGENT", "MERCHANT_AGENT", "RECOVERY_REJECTED",
            (payload.reason or "").strip() if payload and payload.reason else "The buyer declined the revised proposal.",
            metadata={"buyer_feedback": (payload.reason or "").strip() if payload and payload.reason else None},
        )
        db.refresh(deal)
        return _deal(deal, db)
    if deal.status != "WAITING_FOR_BUYER":
        raise HTTPException(status_code=409, detail="Deal cannot be rejected in its current state")

    deal.status = "RECOVERING"
    reason = (payload.reason or "").strip() if payload else ""
    deal.rejection_reason = reason or None
    deal.updated_at = datetime.now(timezone.utc)
    db.commit()
    AuditService.log_event(
        db,
        transaction_id,
        "BUYER_AGENT",
        "PROPOSAL_REJECTED",
        "WARN",
        "Buyer rejected the initial merchant proposal."
        + (f" Feedback: {deal.rejection_reason}" if deal.rejection_reason else ""),
        {"buyer_feedback": deal.rejection_reason},
    )
    _send_agent_message(
        db, transaction_id, "BUYER_AGENT", "MERCHANT_AGENT", "OFFER_REJECTED",
        deal.rejection_reason or "The buyer declined the proposal without an additional comment.",
        metadata={"buyer_feedback": deal.rejection_reason},
    )
    AuditService.log_event(
        db,
        transaction_id,
        "RECOVERY_ENGINE",
        "RECOVERY_STARTED",
        "INFO",
        "Recovery Engine is evaluating policy-compliant alternatives using the buyer's feedback."
        if deal.rejection_reason
        else "Recovery Engine is evaluating policy-compliant alternatives.",
        {"buyer_feedback": deal.rejection_reason},
    )

    policy = db.scalars(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy")).first() or MerchantPolicy()
    initial_items = (deal.initial_offer_json or {}).get("items", [])
    sku = initial_items[0].get("sku") if initial_items else None
    product = db.scalars(select(Product).where(Product.sku == sku)).first() if sku else None
    if not product:
        deal.status = "LOST"
        response = {
            "response_type": "NO_INVENTORY",
            "message": "I can no longer find sufficient inventory for the requested product.",
            "inventory_available": False,
            "requested_budget_paise": deal.max_budget_paise,
            "catalog_total_paise": None,
            "closest_offer_price_paise": None,
            "budget_gap_paise": 0,
            "discount_attempted": False,
            "policy_reasons": [],
            "suggested_actions": ["REDUCE_QUANTITY", "ALLOW_ALTERNATIVES", "MODIFY_REQUIREMENTS"],
        }
        db.commit()
        _publish_merchant_response(db, deal, response)
        db.refresh(deal)
        return _deal(deal, db)

    budget_rupees = deal.max_budget_paise // 100
    reason = (deal.rejection_reason or "").lower()
    price_focused = any(word in reason for word in ("price", "expensive", "cheaper", "budget", "discount"))
    alternative_focused = any(word in reason for word in ("alternative", "different", "brand", "model"))
    candidates = [RecoveryDiscountGenerator.generate(db, product, deal.quantity, budget_rupees, policy)]
    if not price_focused and not alternative_focused:
        candidates.append(OverstockBundleGenerator.generate(db, product, deal.quantity, budget_rupees, policy))
    candidates.append(ProductSubstituteGenerator.generate(db, product, deal.quantity, budget_rupees, policy))
    initial_total_rupees = (deal.initial_offer_json or {}).get("total_price_paise", 0) // 100
    viable_candidates = [
        candidate
        for candidate in candidates
        if candidate and candidate.total_price_rupees < initial_total_rupees
    ]
    ranked = DeterministicScoringEngine.rank_candidates(
        viable_candidates, budget_rupees, policy
    )
    AuditService.log_event(
        db, transaction_id, "RECOVERY_ENGINE", "STRATEGIES_GENERATED", "INFO",
        f"Generated {len(ranked)} deterministic recovery candidates.",
        {"candidate_count": len(ranked)},
    )
    if not ranked:
        deal.status = "LOST"
        deal.current_offer_json = None
        response = {
            "response_type": "NO_FEASIBLE_OFFER",
            "message": "I evaluated the available inventory but could not construct a lower, policy-compliant revised offer. Try changing the budget, quantity, or allowed products.",
            "inventory_available": product.stock_quantity >= deal.quantity,
            "requested_budget_paise": deal.max_budget_paise,
            "catalog_total_paise": product.selling_price_rupees * deal.quantity * 100,
            "closest_offer_price_paise": None,
            "budget_gap_paise": max(0, product.selling_price_rupees * deal.quantity * 100 - deal.max_budget_paise),
            "discount_attempted": True,
            "policy_reasons": [],
            "suggested_actions": ["INCREASE_BUDGET", "REDUCE_QUANTITY", "ALLOW_ALTERNATIVES"],
        }
        db.commit()
        _publish_merchant_response(db, deal, response)
        db.refresh(deal)
        return _deal(deal, db)

    winner = ranked[0]
    hard_specs = (deal.intelligence_json or {}).get("hard_specs") or {}
    passed, gates = control_plane.evaluate_candidate(
        db=db,
        transaction_id=transaction_id,
        candidate=winner.candidate,
        max_budget_rupees=budget_rupees,
        policy=policy,
        buyer_spec_requirements={key: value for key, value in hard_specs.items() if value is not None},
        mandate={
            "max_amount": budget_rupees,
            "allowed_categories": ["LAPTOP", "ACCESSORY", "MONITOR"],
            "expires_at": "2028-12-31T23:59:59Z",
            "transaction_id": transaction_id,
        },
    )
    formatted = {
        "offer_id": winner.candidate.candidate_id,
        "transaction_id": transaction_id,
        "strategy": winner.candidate.strategy.value,
        "explanation": winner.candidate.explanation,
        "total_price_paise": winner.candidate.total_price_rupees * 100,
        "margin_percent": winner.candidate.margin_percent,
        "discount_percent": winner.candidate.discount_percent,
        "final_score": winner.final_score,
        "items": [item.model_dump() for item in winner.candidate.items],
    }
    deal.candidates_json = [
        {
            "strategy": scored.candidate.strategy.value,
            "name": scored.candidate.strategy.value.replace("_", " ").title(),
            "total_price_paise": scored.candidate.total_price_rupees * 100,
            "margin_percent": scored.candidate.margin_percent,
            "discount_percent": scored.candidate.discount_percent,
            "score": scored.final_score,
            "status": "WINNER" if scored.candidate.candidate_id == winner.candidate.candidate_id else "ALTERNATIVE",
            "note": scored.candidate.explanation,
        }
        for scored in ranked
    ]
    deal.gate_results_json = [gate.model_dump() for gate in gates]
    deal.current_offer_json = formatted if passed else None
    deal.status = "RECOVERY_OFFER_SENT" if passed else "LOST"
    deal.outcome_type = "RECOVERY_OFFER"
    deal.updated_at = datetime.now(timezone.utc)
    db.commit()
    AuditService.log_event(db, transaction_id, "SCORING_ENGINE", "STRATEGY_SELECTED", "PASS" if passed else "FAIL", f"Selected {winner.candidate.strategy.value} with score {winner.final_score}.", {"score": winner.final_score, "strategy": winner.candidate.strategy.value})
    if passed:
        response = _merchant_response(
            {"offer": formatted, "catalog_total_paise": product.selling_price_rupees * deal.quantity * 100, "candidates": deal.candidates_json, "gate_results": deal.gate_results_json},
            product, deal.quantity, deal.max_budget_paise,
        )
        _publish_merchant_response(db, deal, response, "RECOVERY_OFFER_SENT")
    else:
        response = _merchant_response(
            {"offer": None, "catalog_total_paise": product.selling_price_rupees * deal.quantity * 100, "candidates": deal.candidates_json, "gate_results": deal.gate_results_json},
            product, deal.quantity, deal.max_budget_paise,
        )
        _publish_merchant_response(db, deal, response)
    db.refresh(deal)
    return _deal(deal, db)


@router.post("/deals/{transaction_id}/accept")
def accept_deal(transaction_id: str, db: Session = Depends(get_db)):
    deal = db.get(Deal, transaction_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status not in {"WAITING_FOR_BUYER", "RECOVERY_OFFER_SENT"} or not deal.current_offer_json:
        raise HTTPException(status_code=409, detail="Deal has no active offer")
    deal.recovered = deal.status == "RECOVERY_OFFER_SENT"
    deal.status = "COMPLETED"
    deal.outcome_type = "RECOVERED" if deal.recovered else "DIRECT_MATCH"
    deal.completed_at = datetime.now(timezone.utc)
    deal.updated_at = deal.completed_at
    db.commit()
    order = payments.create_order(
        deal.current_offer_json["total_price_paise"],
        "INR",
        f"rcpt_{transaction_id}",
    )
    AuditService.log_event(db, transaction_id, "BUYER_AGENT", "PURCHASE_APPROVED", "PASS", "Buyer authorized the final purchase.", {"offer_id": deal.current_offer_json["offer_id"]})
    AuditService.log_event(db, transaction_id, "COMMERCE_CONTROL", "DEAL_COMPLETED", "PASS", "Deal completed and payment order created.", {"order_id": order["id"], "recovered": deal.recovered})
    db.refresh(deal)
    return {"deal": _deal(deal, db), "order": order}


@router.get("/catalog")
def get_catalog(db: Session = Depends(get_db)):
    products = db.scalars(select(Product).order_by(Product.category, Product.name)).all()
    return {"products": [
        {
            "sku": product.sku,
            "name": product.name,
            "brand": product.brand,
            "model": product.model,
            "category": product.category,
            "selling_price_paise": product.selling_price_rupees * 100,
            "cost_price_paise": product.cost_price_rupees * 100,
            "stock_quantity": product.stock_quantity,
            "margin_percent": round(((product.selling_price_rupees - product.cost_price_rupees) / product.selling_price_rupees) * 100, 2),
            "is_overstock": product.is_overstock,
            "is_active": product.is_active,
        }
        for product in products
    ]}


@router.get("/merchant-inbox")
def merchant_inbox(db: Session = Depends(get_db)):
    from app.db.models.buyer_draft import BuyerDraft
    drafts = db.scalars(select(BuyerDraft).where(BuyerDraft.state.in_(["SENT", "WAITING", "REPLIED", "COMPLETED", "DECLINED"]))).all()
    return {"requests": [{"id": d.id, "state": d.state, "requirements": d.data.get("requirements", {}), "transaction_id": d.transaction_id} for d in drafts][-20:]}


@router.get("/merchant-policy")
def get_merchant_policy(db: Session = Depends(get_db)):
    policy = db.scalars(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy")).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Merchant policy not found")
    return _policy(policy)


@router.put("/merchant-policy")
def update_merchant_policy(payload: PolicyUpdate, db: Session = Depends(get_db)):
    policy = db.scalars(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy")).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Merchant policy not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(policy, key, value)
    db.commit()
    db.refresh(policy)
    return _policy(policy)


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    deals = list(db.scalars(select(Deal)).all())
    completed = [deal for deal in deals if deal.status == "COMPLETED"]
    recovered = [deal for deal in completed if deal.recovered]
    lost = [deal for deal in deals if deal.status == "LOST"]
    revenue = sum((deal.current_offer_json or {}).get("total_price_paise", 0) for deal in completed)
    recovered_revenue = sum((deal.current_offer_json or {}).get("total_price_paise", 0) for deal in recovered)
    recovered_profit = sum(
        (deal.current_offer_json or {}).get("total_price_paise", 0)
        - sum(item.get("total_cost_rupees", 0) * 100 for item in (deal.current_offer_json or {}).get("items", []))
        for deal in recovered
    )
    margins = [(deal.current_offer_json or {}).get("margin_percent") for deal in completed]
    margins = [margin for margin in margins if margin is not None]
    recovery_attempts = [deal for deal in deals if deal.recovered or deal.status in {"RECOVERY_OFFER_SENT", "LOST"}]
    return {
        "revenue_paise": revenue,
        "deals_completed": len(completed),
        "sales_recovered": len(recovered),
        "average_margin_percent": round(sum(margins) / len(margins), 2) if margins else 0,
        "rejected_proposals": len(recovery_attempts),
        "recovery_attempts": len(recovery_attempts),
        "recovered_sales": len(recovered),
        "recovery_rate_percent": round(len(recovered) / len(recovery_attempts) * 100, 1) if recovery_attempts else 0,
        "revenue_recovered_paise": recovered_revenue,
        "profit_recovered_paise": recovered_profit,
        "outcomes": {
            "direct_match": len([deal for deal in completed if not deal.recovered]),
            "recovered": len(recovered),
            "lost": len(lost),
        },
    }
