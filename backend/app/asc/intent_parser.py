from app.domain.schemas import BuyerRequest, BuyerRequestItem
from app.llm.contracts import IntentIntelligence
from app.llm.service import IntentIntelligenceService

class IntentParser:
    """Facade preserving the Phase 1 API while exposing Phase 5 intelligence."""

    @staticmethod
    def parse_natural_language(text: str, request_id: str = "REQ-001") -> BuyerRequest:
        request, _ = IntentParser.parse_with_intelligence(text, request_id)
        return request

    @staticmethod
    def parse_with_intelligence(
        text: str,
        request_id: str = "REQ-001",
        service: IntentIntelligenceService | None = None,
    ) -> tuple[BuyerRequest, IntentIntelligence]:
        intelligence = (service or IntentIntelligenceService()).analyze(text)
        request = BuyerRequest(
            request_id=request_id,
            items=[BuyerRequestItem(
                product_query=intelligence.product_query,
                quantity=intelligence.quantity,
            )],
            max_budget_paise=intelligence.max_budget_paise,
            currency=intelligence.currency,
            max_delivery_days=intelligence.max_delivery_days,
            preferences=intelligence.preferences,
            mandate_id="MANDATE-DEMO-001",
        )
        return request, intelligence
