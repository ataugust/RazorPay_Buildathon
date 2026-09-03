from typing import Optional, Dict, Any
from pydantic import BaseModel

class GateResult(BaseModel):
    gate: str              # e.g., "MARGIN_GATE", "INVENTORY_GATE", "SPECIFICATION_GATE"
    status: str            # "PASS" or "FAIL"
    expected: str          # e.g., ">= 15%", ">= 16GB RAM", "<= Rs. 2,40,000"
    actual: str            # e.g., "12.81%", "8GB RAM", "Rs. 2,50,000"
    reason: str            # Human-readable failure or success reason
    metadata: Optional[Dict[str, Any]] = None
