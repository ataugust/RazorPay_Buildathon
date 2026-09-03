from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
from app.domain.models import BuyerRequest, Offer, MerchantPolicy

class GateResult:
    def __init__(self, passed: bool, gate_name: str, message: str, metadata: Dict[str, Any] = None):
        self.passed = passed
        self.gate_name = gate_name
        self.message = message
        self.metadata = metadata or {}

class BaseGate(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, offer: Offer, request: BuyerRequest, policy: MerchantPolicy) -> GateResult:
        pass
