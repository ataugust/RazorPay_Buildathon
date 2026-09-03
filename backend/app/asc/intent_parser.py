import re
from typing import Optional
from app.domain.models import BuyerRequest, BuyerRequestItem

class IntentParser:
    """Parses natural language requests into structured BuyerRequest objects."""
    
    @staticmethod
    def parse_natural_language(text: str, request_id: str = "REQ-001") -> BuyerRequest:
        # Quantity regex
        qty_match = re.search(r"(\d+)\s*(?:lenovo|ideapad|thinkpad|laptops|units|items)", text, re.IGNORECASE)
        quantity = int(qty_match.group(1)) if qty_match else 20
        
        # Budget regex - look explicitly for budget keywords or currency symbols with numbers
        budget_match = re.search(r"(?:budget|max|maximum|up to)\s*(?:of|is)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(lakh|lakhs|l|k|crore|cr)?", text, re.IGNORECASE)
        if not budget_match:
            budget_match = re.search(r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)\s*(lakh|lakhs|l|k|crore|cr)?", text, re.IGNORECASE)

        # Calculate budget in integer paise (Default 25 Lakhs = ₹25,00,000 = 250000000 paise)
        budget_paise = 250000000
        if budget_match:
            val = float(budget_match.group(1))
            unit = (budget_match.group(2) or "").lower()
            if unit in ["lakh", "lakhs", "l"]:
                budget_paise = int(val * 100000 * 100)
            elif unit in ["k"]:
                budget_paise = int(val * 1000 * 100)
            elif unit in ["crore", "cr"]:
                budget_paise = int(val * 10000000 * 100)
            else:
                budget_paise = int(val * 100)

        # Identify product
        product_query = "Lenovo IdeaPad"
        if "thinkpad" in text.lower():
            product_query = "Lenovo ThinkPad"

        return BuyerRequest(
            request_id=request_id,
            items=[BuyerRequestItem(product_query=product_query, quantity=quantity)],
            max_budget_paise=budget_paise,
            currency="INR",
            max_delivery_days=7,
            preferences=[],
            mandate_id="MANDATE-DEMO-001"
        )
