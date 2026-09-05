"""End-to-end buyer rejection, recovery, completion, and merchant sync test."""

import os
import tempfile
import unittest
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "asc_synchronized_deal_flow.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["ASC_LLM_PROVIDER"] = "deterministic"

from fastapi.testclient import TestClient

from app.db.session import engine
from app.main import app


class SynchronizedDealFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()
        from app.api.access import passcode
        cls.client.post("/api/merchant-session", json={"password": passcode()})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.context.__exit__(None, None, None)
        engine.dispose()
        if TEST_DB.exists():
            TEST_DB.unlink()

    def test_buyer_and_merchant_share_one_persistent_deal(self) -> None:
        created = self.client.post(
            "/api/deals",
            json={"prompt": "Buy 5 HP monitors. Maximum total budget Rs 70,000."},
        )
        self.assertEqual(created.status_code, 200, created.text)
        deal = created.json()
        transaction_id = deal["transaction_id"]
        self.assertEqual(deal["quantity"], 5)
        self.assertEqual(deal["max_budget_paise"], 7_000_000)
        self.assertEqual(deal["current_offer"]["total_price_paise"], 6_900_000)
        self.assertEqual(deal["status"], "WAITING_FOR_BUYER")

        rejected = self.client.post(f"/api/deals/{transaction_id}/reject")
        self.assertEqual(rejected.status_code, 200, rejected.text)
        recovery = rejected.json()
        self.assertEqual(recovery["status"], "RECOVERY_OFFER_SENT")
        self.assertLess(
            recovery["current_offer"]["total_price_paise"],
            deal["initial_offer"]["total_price_paise"],
        )
        self.assertTrue(recovery["candidates"])

        accepted = self.client.post(f"/api/deals/{transaction_id}/accept")
        self.assertEqual(accepted.status_code, 200, accepted.text)
        completed = accepted.json()["deal"]
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertTrue(completed["recovered"])

        merchant_view = self.client.get(f"/api/deals/{transaction_id}").json()
        self.assertEqual(merchant_view["status"], "COMPLETED")
        self.assertEqual(
            merchant_view["current_offer"]["total_price_paise"],
            completed["current_offer"]["total_price_paise"],
        )

        analytics = self.client.get("/api/analytics").json()
        self.assertEqual(analytics["sales_recovered"], 1)
        self.assertEqual(analytics["deals_completed"], 1)

        catalog = self.client.get("/api/catalog").json()["products"]
        self.assertTrue(any(product["sku"] == "MON-000" for product in catalog))
        policy = self.client.get("/api/merchant-policy")
        self.assertEqual(policy.status_code, 200)

    def test_missing_details_request_clarification_without_creating_a_deal(self) -> None:
        response = self.client.post(
            "/api/deals",
            json={"prompt": "Help me buy some mouse for market price"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["requires_clarification"])
        self.assertEqual(payload["known_fields"]["product_query"], "Wireless Mouse")
        self.assertEqual(
            set(payload["missing_fields"]),
            {"quantity", "max_budget_paise"},
        )
        deals = self.client.get("/api/deals").json()["deals"]
        self.assertFalse(
            any(deal["prompt"] == "Help me buy some mouse for market price" for deal in deals)
        )

    def test_rejection_comment_is_persisted_and_guides_recovery(self) -> None:
        created = self.client.post(
            "/api/deals",
            json={"prompt": "Buy 5 HP monitors. Maximum total budget Rs 70,000."},
        ).json()
        rejected = self.client.post(
            f"/api/deals/{created['transaction_id']}/reject",
            json={"reason": "The price is too expensive; please find a cheaper option."},
        )
        self.assertEqual(rejected.status_code, 200, rejected.text)
        payload = rejected.json()
        self.assertEqual(
            payload["rejection_reason"],
            "The price is too expensive; please find a cheaper option.",
        )
        rejection_event = next(
            event for event in payload["events"]
            if event["event_type"] == "PROPOSAL_REJECTED"
        )
        self.assertEqual(
            rejection_event["metadata"]["buyer_feedback"],
            payload["rejection_reason"],
        )

    def test_policy_violation_ends_recovery_safely(self) -> None:
        try:
            created = self.client.post(
                "/api/deals",
                json={"prompt": "Buy 5 HP monitors. Maximum total budget Rs 70,000."},
            ).json()
            self.assertEqual(created["status"], "WAITING_FOR_BUYER")
            policy = self.client.put(
                "/api/merchant-policy",
                json={"min_margin_percent": 90.0},
            )
            self.assertEqual(policy.status_code, 200)
            rejected = self.client.post(
                f"/api/deals/{created['transaction_id']}/reject"
            )
            self.assertEqual(rejected.status_code, 200, rejected.text)
            self.assertEqual(rejected.json()["status"], "LOST")
            self.assertIsNone(rejected.json()["current_offer"])
        finally:
            self.client.put(
                "/api/merchant-policy",
                json={"min_margin_percent": 15.0},
            )

    def test_impossible_budget_returns_explained_merchant_reply(self) -> None:
        created = self.client.post(
            "/api/deals",
            json={"prompt": "Buy 5 monitors. Maximum total budget Rs 20,000."},
        )
        self.assertEqual(created.status_code, 200, created.text)
        deal = created.json()
        self.assertEqual(deal["status"], "LOST")
        self.assertIsNone(deal["current_offer"])
        reply = deal["merchant_response"]
        self.assertEqual(reply["response_type"], "BUDGET_TOO_LOW")
        self.assertTrue(reply["inventory_available"])
        self.assertGreater(reply["catalog_total_paise"], deal["max_budget_paise"])
        self.assertGreater(reply["closest_offer_price_paise"], deal["max_budget_paise"])
        self.assertEqual(
            reply["budget_gap_paise"],
            reply["closest_offer_price_paise"] - deal["max_budget_paise"],
        )
        self.assertIn("policy-compliant", reply["message"])
        self.assertTrue(any(message["message_type"] == "PURCHASE_REQUEST" for message in deal["messages"]))
        self.assertTrue(any(message["message_type"] == "UNABLE_TO_OFFER" for message in deal["messages"]))
        event_types = [event["event_type"] for event in deal["events"]]
        self.assertIn("MERCHANT_RESPONSE_SENT", event_types)
        self.assertNotIn("PROPOSAL_SENT", event_types)

        messages = self.client.get(
            f"/api/deals/{deal['transaction_id']}/messages"
        )
        self.assertEqual(messages.status_code, 200)
        self.assertEqual(len(messages.json()["messages"]), 2)

    def test_unknown_product_and_insufficient_stock_are_not_called_budget_failures(self) -> None:
        unknown = self.client.post(
            "/api/deals",
            json={"prompt": "Product: Projector. Quantity: 5. Maximum total budget Rs 500,000."},
        )
        self.assertEqual(unknown.status_code, 200, unknown.text)
        unknown_deal = unknown.json()
        self.assertEqual(unknown_deal["merchant_response"]["response_type"], "NO_INVENTORY")
        self.assertFalse(unknown_deal["merchant_response"]["inventory_available"])
        self.assertNotIn("PROPOSAL_SENT", [event["event_type"] for event in unknown_deal["events"]])

        insufficient = self.client.post(
            "/api/deals",
            json={"prompt": "Buy 600 mouse. Maximum total budget Rs 2,400,000."},
        )
        self.assertEqual(insufficient.status_code, 200, insufficient.text)
        insufficient_deal = insufficient.json()
        self.assertEqual(insufficient_deal["merchant_response"]["response_type"], "NO_INVENTORY")
        self.assertFalse(insufficient_deal["merchant_response"]["inventory_available"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
