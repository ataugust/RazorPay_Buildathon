"""Unit checks for the Razorpay security boundary; no network or money movement."""
import hashlib
import hmac
import unittest
from unittest.mock import Mock, patch

from app.payments.base import PaymentProviderError, RazorpayPaymentProvider


class RazorpayCheckoutTests(unittest.TestCase):
    def test_signature_uses_server_order_and_secret(self):
        provider = RazorpayPaymentProvider("rzp_test_public", "server-secret")
        signature = hmac.new(b"server-secret", b"order_123|pay_456", hashlib.sha256).hexdigest()
        self.assertTrue(provider.verify_payment("pay_456", "order_123", signature))
        self.assertFalse(provider.verify_payment("pay_tampered", "order_123", signature))

    def test_missing_credentials_fail_closed(self):
        with patch.dict("os.environ", {"RAZORPAY_KEY_ID": "", "RAZORPAY_KEY_SECRET": ""}):
            with self.assertRaises(PaymentProviderError):
                RazorpayPaymentProvider().create_order(50000, "INR", "receipt")

    @patch("app.payments.base.httpx.request")
    def test_order_amount_and_currency_are_validated(self, request):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "order_123", "amount": 50000, "currency": "INR", "status": "created"}
        request.return_value = response
        provider = RazorpayPaymentProvider("rzp_test_public", "server-secret")
        order = provider.create_order(50000, "INR", "receipt")
        self.assertEqual(order["id"], "order_123")
        sent = request.call_args.kwargs
        self.assertEqual(sent["auth"], ("rzp_test_public", "server-secret"))
        self.assertEqual(sent["json"]["amount"], 50000)


if __name__ == "__main__":
    unittest.main()
