"""Phase 5 tests: extraction, provider fallback, bounded output, and direct offers."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


TEST_DB = Path(tempfile.gettempdir()) / "asc_phase5_integration.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["ASC_LLM_PROVIDER"] = "deterministic"

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.db.session import engine
from app.asc.orchestrator import ASCOrchestrator
from app.domain.schemas import BuyerRequest, BuyerRequestItem
from app.domain.strategy_types import AllowedStrategy
from app.llm.contracts import HardSpecifications, IntentIntelligence
from app.llm.providers import CloudLLMProvider, GeminiFlashProvider, LLMProvider, RuleBasedIntentProvider
from app.llm.service import IntentIntelligenceService
from app.main import app


class FailingProvider(LLMProvider):
    name = "failing-test-provider"
    model = "test"

    def analyze(self, text: str) -> IntentIntelligence:
        raise TimeoutError("simulated timeout")


class DirectOnlyProvider(LLMProvider):
    name = "gemini"
    model = "test-flash"

    def analyze(self, text: str) -> IntentIntelligence:
        return IntentIntelligence(
            product_query="mouse",
            quantity=5,
            max_budget_paise=400_000,
            recommended_strategies=[AllowedStrategy.DIRECT_MATCH],
            provider=self.name,
            model=self.model,
        )


class PhaseFiveTest(unittest.TestCase):
    def test_llm_cannot_remove_deterministic_recovery_strategies(self) -> None:
        result = IntentIntelligenceService(provider=DirectOnlyProvider()).analyze(
            "buy me 5 mouse maximum budget 4000"
        )
        self.assertIn(AllowedStrategy.DIRECT_MATCH, result.recommended_strategies)
        self.assertIn(AllowedStrategy.VOLUME_DISCOUNT, result.recommended_strategies)
        self.assertIn(AllowedStrategy.BUNDLE_OVERSTOCK, result.recommended_strategies)

    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()
        from app.api.access import passcode
        cls.client.post("/api/merchant-session", json={"password": passcode()})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        engine.dispose()
        if TEST_DB.exists():
            TEST_DB.unlink()

    def test_rule_parser_extracts_constraints(self) -> None:
        result = RuleBasedIntentProvider().analyze(
            "We need around twenty developer laptops with at least 16GB RAM, "
            "512GB SSD and i7. Budget is roughly Rs 24.5 lakhs; delivery within 5 days is non-negotiable."
        )
        self.assertEqual(result.quantity, 20)
        self.assertEqual(result.max_budget_paise, 245_000_000)
        self.assertEqual(result.max_delivery_days, 5)
        self.assertEqual(result.hard_specs.min_ram_gb, 16)
        self.assertEqual(result.hard_specs.min_storage_gb, 512)
        self.assertEqual(result.hard_specs.min_cpu_tier, "i7")
        self.assertIn(
            AllowedStrategy.QUANTITY_ADJUSTMENT,
            result.recommended_strategies,
        )

    def test_provider_failure_falls_back_without_leaking_error_details(self) -> None:
        result = IntentIntelligenceService(FailingProvider()).analyze(
            "Order 20 Lenovo IdeaPad laptops under Rs 24L"
        )
        self.assertEqual(result.provider, "deterministic_fallback")
        self.assertIn("TimeoutError", result.fallback_reason)
        self.assertNotIn("simulated timeout", result.fallback_reason)

    def test_unapproved_strategy_is_rejected_by_schema(self) -> None:
        provider = CloudLLMProvider("https://invalid.test", "secret", "test-model")
        with self.assertRaises(ValidationError):
            provider._validate({
                "product_query": "Lenovo IdeaPad",
                "quantity": 20,
                "max_budget_paise": 240_000_000,
                "recommended_strategies": ["FREE_GIFT"],
            })

    def test_intelligence_cannot_relax_product_without_buyer_permission(self) -> None:
        intelligence = IntentIntelligence(
            product_query="Lenovo IdeaPad",
            quantity=20,
            max_budget_paise=240_000_000,
            hard_specs=HardSpecifications(min_ram_gb=16),
            recommended_strategies=[AllowedStrategy.PRODUCT_SUBSTITUTE],
            strategy_rationale="Use the permitted in-catalog substitute path.",
            provider="test",
        )
        result = ASCOrchestrator().process_purchase_request(
            BuyerRequest(
                request_id="REQ-BOUND-001",
                items=[BuyerRequestItem(product_query="Lenovo IdeaPad", quantity=20)],
                max_budget_paise=240_000_000,
            ),
            intelligence,
        )
        self.assertEqual(result["offer"]["strategy"], "VOLUME_DISCOUNT")
        self.assertTrue(all("IdeaPad" in item["name"] for item in result["offer"]["items"]))

    def test_prompt_endpoint_exposes_intelligence_and_audits_it(self) -> None:
        response = self.client.post(
            "/api/purchase/prompt",
            json={"prompt": "Order 20 Lenovo IdeaPad laptops under Rs 24L"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["intelligence"]["provider"], "deterministic")
        self.assertTrue(payload["result"]["transaction_id"].startswith("TXN-"))
        strategies = {
            AllowedStrategy(value)
            for value in payload["intelligence"]["recommended_strategies"]
        }
        self.assertIn(AllowedStrategy.VOLUME_DISCOUNT, strategies)

        audit = self.client.get(
            f"/api/audit/transaction/{payload['result']['transaction_id']}"
        ).json()
        self.assertIn(
            "INTENT_NORMALIZED",
            {event["event_type"] for event in audit["events"]},
        )

    def test_direct_match_uses_catalog_price(self) -> None:
        response = self.client.post(
            "/api/purchase/prompt",
            json={"prompt": "Order 20 Lenovo IdeaPad laptops under Rs 27L"},
        )
        result = response.json()["result"]
        self.assertTrue(result["rescued"])
        self.assertEqual(result["offer"]["strategy"], "DIRECT_MATCH")
        self.assertEqual(result["offer"]["total_price_paise"], 250_000_000)
        self.assertEqual(result["offer"]["discount_percent"], 0.0)
        self.assertEqual(result["outcome_type"], "DIRECT_MATCH")
        self.assertEqual(result["catalog_total_paise"], 250_000_000)
        self.assertEqual(len(result["candidates"]), 1)

    @patch("app.llm.providers.httpx.post")
    def test_gemini_flash_uses_structured_json_and_bounded_schema(self, post: Mock) -> None:
        payload = {
            "product_query": "Dell Inspiron 14",
            "quantity": 4,
            "max_budget_paise": 30_000_000,
            "currency": "INR",
            "max_delivery_days": 7,
            "hard_specs": {"min_ram_gb": 16, "min_cpu_tier": "i5", "min_storage_gb": 512},
            "preferences": [],
            "recommended_strategies": ["VOLUME_DISCOUNT", "PRODUCT_SUBSTITUTE"],
            "strategy_rationale": "Compare bounded deterministic options.",
            "confidence": 0.94,
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"candidates": [{"content": {"parts": [{"text": __import__("json").dumps(payload)}]}}]}
        post.return_value = response

        result = GeminiFlashProvider("test-key", "gemini-3.5-flash").analyze("Buy four Dell laptops")
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(result.model, "gemini-3.5-flash")
        self.assertEqual(result.quantity, 4)
        request_payload = post.call_args.kwargs["json"]
        self.assertEqual(request_payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-key")


if __name__ == "__main__":
    unittest.main(verbosity=2)
