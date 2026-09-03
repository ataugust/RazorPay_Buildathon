from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.domain.models import BuyerRequest
from app.asc.intent_parser import IntentParser
from app.asc.orchestrator import ASCOrchestrator
from app.payments.base import MockPaymentProvider

router = APIRouter(prefix="/api/purchase", tags=["Purchase"])
orchestrator = ASCOrchestrator()
payment_provider = MockPaymentProvider()

class NaturalLanguagePurchasePayload(BaseModel):
    prompt: str

@router.post("/request")
def process_purchase_request(request: BuyerRequest):
    """Processes structured buyer requests through the ASC engine."""
    result = orchestrator.process_purchase_request(request)
    return result

@router.post("/prompt")
def process_natural_language_prompt(payload: NaturalLanguagePurchasePayload):
    """Parses natural language purchase intent and executes ASC transaction engine."""
    buyer_request = IntentParser.parse_natural_language(payload.prompt)
    result = orchestrator.process_purchase_request(buyer_request)
    return {
        "parsed_request": buyer_request,
        "result": result
    }

@router.post("/execute-payment/{transaction_id}")
def execute_payment(transaction_id: str, offer_id: str, amount_paise: int):
    """Executes order payment using the configured payment provider."""
    order = payment_provider.create_order(
        amount_paise=amount_paise,
        currency="INR",
        receipt=f"rcpt_{transaction_id}"
    )
    return {
        "status": "SUCCESS",
        "transaction_id": transaction_id,
        "order": order
    }
