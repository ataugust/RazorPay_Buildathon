from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePaymentProvider(ABC):
    @abstractmethod
    def create_order(self, amount_paise: int, currency: str, receipt: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def verify_payment(self, payment_id: str, order_id: str, signature: str) -> bool:
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

class RazorpayPaymentProvider(BasePaymentProvider):
    def __init__(self, key_id: str = "rzp_test_mock", key_secret: str = "mock_secret"):
        self.key_id = key_id
        self.key_secret = key_secret

    def create_order(self, amount_paise: int, currency: str, receipt: str) -> Dict[str, Any]:
        import uuid
        # Stub for Razorpay SDK order creation
        return {
            "id": f"order_rzp_{uuid.uuid4().hex[:10]}",
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
            "provider": "RAZORPAY_TEST"
        }

    def verify_payment(self, payment_id: str, order_id: str, signature: str) -> bool:
        return True
