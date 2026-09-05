"""Regressions for real buyer requests, explicit budgets and private merchant data."""
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

folder = tempfile.TemporaryDirectory(prefix="asc-buyer-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(folder.name).as_posix()}/test.db"
os.environ["ASC_LLM_PROVIDER"] = "deterministic"
from fastapi.testclient import TestClient
from app.main import app
from app.api.buyer import extract
from app.api.access import passcode
from app.db.session import SessionLocal, engine
from app.db.models.product import Product
from app.asc.catalog_search import find_products


class BuyerBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()
        cls.client.post("/api/buyer/session")

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None,None,None)
        engine.dispose()
        folder.cleanup()

    def submit(self, prompt):
        start = self.client.post("/api/buyer/requests", json={"prompt":prompt})
        self.assertEqual(start.status_code,202,start.text)
        self.assertEqual(start.json()["state"],"PREPARING")
        return self.client.get("/api/buyer/requests/"+start.json()["id"]).json()

    def pay(self, purchase):
        amount = purchase["offer"]["total_price_paise"]
        order_id = f"order_test_{purchase['id'][:8]}"
        with patch("app.api.buyer.RazorpayPaymentProvider") as provider_type:
            provider = provider_type.return_value
            provider.key_id = "rzp_test_public"
            provider.create_order.return_value = {"id": order_id, "amount": amount, "currency": "INR", "status": "created"}
            provider.verify_payment.return_value = True
            provider.fetch_payment.return_value = {"id": "pay_test", "order_id": order_id, "amount": amount,
                                                     "currency": "INR", "status": "captured", "captured": True}
            checkout = self.client.post(f"/api/buyer/requests/{purchase['id']}/checkout")
            self.assertEqual(checkout.status_code, 200, checkout.text)
            self.assertEqual(checkout.json()["purchase"]["state"], "PAYMENT_PENDING")
            verified = self.client.post(f"/api/buyer/requests/{purchase['id']}/payment/verify", json={
                "razorpay_payment_id": "pay_test", "razorpay_order_id": order_id,
                "razorpay_signature": "a" * 64,
            })
            return verified

    def test_exact_laptop_prompt_finds_offer(self):
        result=self.submit("Buy me 2 laptops max budget 1 lakh rupees")
        self.assertEqual(result["state"],"REPLIED",result)
        self.assertEqual(result["requirements"]["quantity"],2)
        self.assertEqual(result["requirements"]["max_budget_paise"],10000000)
        self.assertIsNotNone(result["offer"], result)
        self.assertLessEqual(result["offer"]["total_price_paise"],10000000)
        self.assertEqual(result["missing_fields"],[])
        self.assertEqual([e["state"] for e in result["events"]],["PREPARING","SENT","WAITING","REPLIED"])

    def test_no_limit_asks_only_quantity_and_persists_answers(self):
        result=self.submit("buy any laptop for me no limit in budget")
        self.assertEqual(result["missing_fields"],["quantity"],result)
        self.assertIsNone(result["requirements"]["max_budget_paise"])
        req={**result["requirements"],"quantity":1}
        with patch("app.api.buyer.extract",side_effect=AssertionError("Must not reparse clarification")):
            update=self.client.patch(f"/api/buyer/requests/{result['id']}",json={"requirements":req})
            self.assertEqual(update.status_code,202,update.text)
        final=self.client.get(f"/api/buyer/requests/{result['id']}").json()
        self.assertEqual(final["state"],"REPLIED",final)
        self.assertIsNotNone(final["offer"])
        self.assertIsNone(final["requirements"]["max_budget_paise"])

    def test_ryzen_ram_constraints_survive_clarification(self):
        result=self.submit("I want to buy 5 laptops with ryzen 5 and 8 gbram")
        self.assertEqual(result["missing_fields"],["budget"],result)
        self.assertEqual(result["requirements"]["hard_specs"]["min_ram_gb"],8)
        self.assertEqual(result["requirements"]["hard_specs"]["min_cpu_tier"],"Ryzen 5")
        req={**result["requirements"],"budget_mode":"no_limit"}
        self.client.patch(f"/api/buyer/requests/{result['id']}",json={"requirements":req})
        final=self.client.get(f"/api/buyer/requests/{result['id']}").json()
        self.assertIsNotNone(final["offer"],final)
        for item in final["offer"]["items"]:
            self.assertGreaterEqual(item["specifications"]["ram_gb"],8)
            self.assertEqual(item["specifications"]["cpu_brand"],"AMD")

    def test_mouse_search_checks_cheaper_catalog_items(self):
        # Place a valid cheap SKU after the existing expensive rows. This is
        # regression data, not a fabricated change to the user's live catalog.
        with SessionLocal() as db:
            db.add(Product(sku="TEST-MOUSE-BASIC", name="Basic USB Mouse", category="ACCESSORY", selling_price_rupees=600, cost_price_rupees=400, stock_quantity=20, is_active=True))
            db.commit()
        result=self.submit("buy me 5 mouse maximum budget 4000")
        self.assertIsNotNone(result["offer"],result)
        self.assertLessEqual(result["offer"]["total_price_paise"],400000)

    def test_private_fields_and_ownership(self):
        result=self.submit("Buy me 2 laptops max budget 1 lakh rupees")
        banned={"provider","model","intelligence","candidates","gate_results","margin_percent","unit_cost_rupees","total_cost_rupees","strategy","policy_reasons"}
        def check(value):
            if isinstance(value,dict):
                self.assertFalse(set(value)&banned)
                for v in value.values():check(v)
            elif isinstance(value,list):
                for v in value:check(v)
        check(result)
        for path in ("/api/catalog","/api/deals","/api/audit/recent","/api/merchant-policy"):
            self.assertEqual(self.client.get(path).status_code,401,path)
        other=TestClient(app)
        other.post("/api/buyer/session")
        self.assertEqual(other.get(f"/api/buyer/requests/{result['id']}").status_code,404)

    def test_unknown_product_does_not_invent_offer(self):
        result=self.submit("Product: quantum banana. Quantity: 2. Maximum total budget Rs 4000")
        self.assertEqual(result["state"],"REPLIED",result)
        self.assertIsNone(result["offer"])
        self.assertNotIn("paise",result["reply"])
        self.assertNotIn("reduce",result["reply"])

    def test_no_limit_variants(self):
        for prompt in ("buy any laptop and I don't have any budget", "buy 2 laptops with no budget limit", "buy 2 laptops unlimited budget"):
            req,_=extract(prompt)
            self.assertEqual(req.budget_mode,"no_limit",prompt)
            self.assertIsNone(req.max_budget_paise)

    def test_merchant_authentication(self):
        merchant=TestClient(app)
        self.assertEqual(merchant.post("/api/merchant-session",json={"password":"wrong"}).status_code,401)
        self.assertEqual(merchant.post("/api/merchant-session",json={"password":passcode()}).status_code,200)
        self.assertEqual(merchant.get("/api/catalog").status_code,200)

    def test_checkout_requires_verified_payment(self):
        result=self.submit("buy 1 laptop no budget limit")
        self.assertEqual(result["state"],"REPLIED")
        accepted=self.pay(result)
        self.assertEqual(accepted.status_code,200,accepted.text)
        self.assertEqual(accepted.json()["state"],"COMPLETED")
        self.assertEqual(self.client.post(f"/api/buyer/requests/{result['id']}/accept").status_code,410)

    def test_stale_stock_cannot_be_approved(self):
        result=self.submit("buy 1 Acer Chromebook Plus laptop max budget 50000")
        self.assertIsNotNone(result["offer"],result)
        from sqlalchemy import select
        with SessionLocal() as db:
            product=db.scalars(select(Product).where(Product.sku==result["offer"]["items"][0]["sku"])).first()
            previous=product.stock_quantity
            product.stock_quantity=0
            db.commit()
        response=self.client.post(f"/api/buyer/requests/{result['id']}/checkout")
        self.assertEqual(response.status_code,409,response.text)
        with SessionLocal() as db:
            product=db.scalars(select(Product).where(Product.sku==result["offer"]["items"][0]["sku"])).first()
            product.stock_quantity=previous
            db.commit()

    def test_revision_and_decline_preserve_request_identity(self):
        result=self.submit("buy 2 laptops max budget 100000")
        decline=self.client.post(f"/api/buyer/requests/{result['id']}/decline",json={"reason":"Please find a cheaper option"})
        self.assertEqual(decline.json()["state"],"DECLINED")
        req={**result["requirements"],"quantity":1,"max_budget_paise":5000000}
        update=self.client.patch(f"/api/buyer/requests/{result['id']}",json={"requirements":req})
        self.assertEqual(update.status_code,202)
        final=self.client.get(f"/api/buyer/requests/{result['id']}").json()
        self.assertEqual(final["id"],result["id"])
        self.assertEqual(final["requirements"]["quantity"],1)
        self.assertLessEqual(final["offer"]["total_price_paise"],5000000)

    def test_provider_timeout_keeps_exact_facts(self):
        from app.llm.providers import GeminiFlashProvider
        with patch("app.api.buyer.IntentIntelligenceService._configured_provider",return_value=GeminiFlashProvider("test-key")), patch.object(GeminiFlashProvider,"_generate",side_effect=TimeoutError()):
            result=self.submit("Buy me 2 laptops max budget 1 lakh rupees")
        self.assertEqual(result["state"],"REPLIED",result)
        self.assertEqual(result["requirements"]["max_budget_paise"],10000000)
        self.assertIsNotNone(result["offer"])


    def test_requested_discount_is_rejected_then_safe_offer_is_returned(self):
        from sqlalchemy import select
        from app.db.models.merchant_policy import MerchantPolicy
        with SessionLocal() as db:
            policy = db.scalars(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy")).first()
            old_margin, old_discount = policy.min_margin_percent, policy.max_discount_percent
            policy.min_margin_percent, policy.max_discount_percent = 12.0, 15.0
            db.commit()
        try:
            draft = self.submit("Give me a 30% discount")
            self.assertEqual(draft["requirements"]["requested_discount_percent"], 30.0)
            self.assertEqual(set(draft["missing_fields"]), {"product_query", "quantity", "budget"})
            req = {**draft["requirements"], "product_query": "laptop", "quantity": 2, "budget_mode": "no_limit"}
            self.client.patch(f"/api/buyer/requests/{draft['id']}", json={"requirements": req})
            final = self.client.get(f"/api/buyer/requests/{draft['id']}").json()
            self.assertIsNotNone(final["offer"], final)
            self.assertIn("cannot approve a 30% discount", final["reply"])
            self.assertNotIn("gate", final["reply"].lower())
            merchant = TestClient(app)
            merchant.post("/api/merchant-session", json={"password": passcode()})
            detail = merchant.get(f"/api/deals/{final['transaction_id']}").json()
            requested = next(c for c in detail["candidates"] if c["strategy"] == "BUYER_REQUESTED_DISCOUNT")
            self.assertEqual(requested["status"], "REJECTED_POLICY")
            discount_gate = next(g for g in requested["gate_results"] if g["gate"] == "DISCOUNT_GATE")
            self.assertEqual(discount_gate["status"], "FAIL")
            self.assertEqual(discount_gate["expected"], "<= 15.0%")
            self.assertEqual(discount_gate["actual"], "30.00%")
            self.assertNotEqual(detail["current_offer"]["strategy"], "BUYER_REQUESTED_DISCOUNT")
        finally:
            with SessionLocal() as db:
                policy = db.scalars(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy")).first()
                policy.min_margin_percent, policy.max_discount_percent = old_margin, old_discount
                db.commit()

    def test_invalid_gemini_json_falls_back_safely(self):
        from app.llm.providers import GeminiFlashProvider
        with patch("app.api.buyer.IntentIntelligenceService._configured_provider", return_value=GeminiFlashProvider("test-key")), patch.object(GeminiFlashProvider, "_generate", return_value="not-json"):
            result = self.submit("Buy me 2 laptops max budget 1 lakh rupees")
        self.assertEqual(result["state"], "REPLIED", result)
        self.assertEqual(result["requirements"]["quantity"], 2)
        self.assertIsNotNone(result["offer"])


    def test_interrupted_request_becomes_retryable_after_restart(self):
        from app.db.models.buyer_draft import BuyerDraft
        from app.main import recover_interrupted_buyer_drafts
        with SessionLocal() as db:
            draft = BuyerDraft(id="f" * 32, owner="e" * 32, prompt="buy a laptop", state="WAITING", data={}, events=[])
            db.add(draft)
            db.commit()
        self.assertGreaterEqual(recover_interrupted_buyer_drafts(), 1)
        with SessionLocal() as db:
            recovered = db.get(BuyerDraft, "f" * 32)
            self.assertEqual(recovered.state, "ERROR")
            self.assertIn("reviewed and retried", recovered.data["error"])


    def test_macbook_overstock_bundle_requires_explicit_revised_budget(self):
        from sqlalchemy import select
        from app.db.models.merchant_policy import MerchantPolicy
        with SessionLocal() as db:
            policy = db.scalars(select(MerchantPolicy).where(MerchantPolicy.policy_name == "default_policy")).first()
            policy.min_margin_percent, policy.max_discount_percent = 12.0, 15.0
            mac = db.scalars(select(Product).where(Product.sku == "LAP-NEO-001")).first()
            mouse = db.scalars(select(Product).where(Product.sku == "ACC-DEMO-MOUSE")).first()
            mac_before, mouse_before = mac.stock_quantity, mouse.stock_quantity
            db.commit()
        initial = self.submit("I want to buy 10 units of macbook neo and maximum budget is 7 lakhs")
        self.assertEqual(initial["state"], "REPLIED", initial)
        self.assertIsNone(initial["offer"], initial)
        started = self.client.post(f"/api/buyer/requests/{initial['id']}/negotiate")
        self.assertEqual(started.status_code, 202, started.text)
        final = self.client.get(f"/api/buyer/requests/{initial['id']}").json()
        self.assertEqual(final["state"], "REPLIED", final)
        self.assertTrue(final["offer"]["requires_budget_approval"])
        self.assertEqual(final["offer"]["original_budget_paise"], 70000000)
        self.assertEqual(final["offer"]["proposed_budget_paise"], 75000000)
        free_mouse = next(item for item in final["offer"]["items"] if item["sku"] == "ACC-DEMO-MOUSE")
        self.assertEqual(free_mouse["quantity"], 10)
        self.assertEqual(free_mouse["unit_price_rupees"], 0)
        accepted = self.pay(final)
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["requirements"]["max_budget_paise"], 75000000)
        with SessionLocal() as db:
            mac = db.scalars(select(Product).where(Product.sku == "LAP-NEO-001")).first()
            mouse = db.scalars(select(Product).where(Product.sku == "ACC-DEMO-MOUSE")).first()
            self.assertEqual(mac.stock_quantity, mac_before - 10)
            self.assertEqual(mouse.stock_quantity, mouse_before - 10)


if __name__ == "__main__": unittest.main()
