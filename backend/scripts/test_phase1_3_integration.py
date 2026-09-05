"""End-to-end verification for the consolidated Phase 1–3 pipeline.

The script uses a temporary SQLite database and never modifies development
data. Run it from ``backend`` with ``python -m scripts.test_phase1_3_integration``.
"""

import os
os.environ["ASC_LLM_PROVIDER"] = "deterministic"
import tempfile
import unittest
from pathlib import Path


TEST_DB = Path(tempfile.gettempdir()) / "asc_phase1_3_integration.db"
if TEST_DB.exists():
    TEST_DB.unlink()

# Define this before importing app modules: the engine reads it on import.
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"

from fastapi.testclient import TestClient

from app.db.session import engine
from app.main import app


class PhaseOneToThreeIntegrationTest(unittest.TestCase):
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

    def test_purchase_and_audit_use_the_same_database(self) -> None:
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "healthy")

        purchase = self.client.post(
            "/api/purchase/prompt",
            json={
                "prompt": (
                    "Buy 20 Lenovo IdeaPad laptops with a maximum budget "
                    "of Rs 24 lakhs"
                )
            },
        )
        self.assertEqual(purchase.status_code, 200, purchase.text)

        result = purchase.json()["result"]
        intelligence = purchase.json()["intelligence"]
        self.assertEqual(intelligence["provider"], "deterministic")
        self.assertTrue(intelligence["recommended_strategies"])
        transaction_id = result["transaction_id"]
        self.assertTrue(transaction_id.startswith("TXN-"))
        self.assertEqual(len(result["gate_results"]), 6)

        audit = self.client.get(f"/api/audit/transaction/{transaction_id}")
        self.assertEqual(audit.status_code, 200, audit.text)

        audit_payload = audit.json()
        self.assertEqual(audit_payload["transaction_id"], transaction_id)
        events = audit_payload["events"]
        self.assertGreaterEqual(len(events), 8)
        self.assertTrue(all(event["transaction_id"] == transaction_id for event in events))

        event_types = {event["event_type"] for event in events}
        self.assertIn("EVALUATION_START", event_types)
        self.assertIn("INTENT_NORMALIZED", event_types)
        self.assertTrue(
            {"CANDIDATE_APPROVED", "CANDIDATE_REJECTED"} & event_types
        )

        gate_events = [
            event for event in events if event["event_type"].startswith("GATE_CHECK_")
        ]
        self.assertEqual(len(gate_events), 6)

        summary = self.client.get("/api/audit/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertGreaterEqual(summary.json()["total_transactions"], 1)

        recent = self.client.get("/api/audit/recent", params={"limit": 5})
        self.assertEqual(recent.status_code, 200)
        self.assertGreater(len(recent.json()["events"]), 0)

        with self.client.stream(
            "GET", f"/api/audit/transaction/{transaction_id}/stream"
        ) as stream:
            self.assertEqual(stream.status_code, 200)
            stream_text = "".join(stream.iter_text())

        self.assertIn("event: audit", stream_text)
        self.assertIn("event: complete", stream_text)
        self.assertIn(transaction_id, stream_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
