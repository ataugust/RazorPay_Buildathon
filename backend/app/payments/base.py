"""Payment provider boundary used by ASC checkout flows."""
from abc import ABC, abstractmethod
import hashlib
import hmac
import os
from typing import Any, Dict

import httpx


class PaymentProviderError(RuntimeError):
    """A safe payment-provider error that may be shown to the buyer."""

class BasePaymentProvider(ABC):
    @abstractmethod
    def create_order(self, amount_paise: int, currency: str, receipt: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def verify_payment(self, payment_id: str, order_id: str, signature: str) -> bool:
        pass

    @abstractmethod
    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        pass

class MockPaymentProvider(BasePaymentProvider):
    def create_order(self, amount_paise: int, currency: str, receipt: str) -> Dict[str, Any]:
        import uuid
        return {
            "id": f"order_mock_{uuid.uuid4().hex[:10]}",
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
            "provider": "MOCK"
        }

    def verify_payment(self, payment_id: str, order_id: str, signature: str) -> bool:
        return True

    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        return {"id": payment_id, "status": "captured", "captured": True}

class RazorpayPaymentProvider(BasePaymentProvider):
    api_base = "https://api.razorpay.com/v1"

    def __init__(self, key_id: str | None = None, key_secret: str | None = None):
        self.key_id = (key_id if key_id is not None else os.getenv("RAZORPAY_KEY_ID", "")).strip()
        self.key_secret = (key_secret if key_secret is not None else os.getenv("RAZORPAY_KEY_SECRET", "")).strip()

    def _require_credentials(self):
        if not self.key_id or not self.key_secret:
            raise PaymentProviderError("Razorpay checkout is not configured. Add test API credentials to the backend and restart it.")

    def _request(self, method: str, path: str, payload: dict | None = None) -> Dict[str, Any]:
        self._require_credentials()
        try:
            response = httpx.request(method, f"{self.api_base}{path}", auth=(self.key_id, self.key_secret),
                                     json=payload, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected response")
            return data
        except (httpx.HTTPError, ValueError) as exc:
            raise PaymentProviderError("Razorpay could not start or verify this payment. Please try again.") from exc

    def create_order(self, amount_paise: int, currency: str, receipt: str) -> Dict[str, Any]:
        if amount_paise < 100:
            raise PaymentProviderError("The payment amount is below Razorpay's supported minimum.")
        order = self._request("POST", "/orders", {
            "amount": int(amount_paise), "currency": currency, "receipt": receipt[:40],
            "notes": {"asc_request_id": receipt[:250]},
        })
        if not order.get("id") or int(order.get("amount", -1)) != amount_paise or order.get("currency") != currency:
            raise PaymentProviderError("Razorpay returned an invalid order. No purchase was completed.")
        return order

    def verify_payment(self, payment_id: str, order_id: str, signature: str) -> bool:
        self._require_credentials()
        expected = hmac.new(self.key_secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/payments/{payment_id}")
