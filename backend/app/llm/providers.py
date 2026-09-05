"""Provider abstraction for structured intent extraction.

Providers can interpret text and recommend an allow-listed strategy. They never
calculate prices, approve offers, or execute payments.
"""

import json
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx
from app.domain.strategy_types import AllowedStrategy
from app.llm.contracts import HardSpecifications, IntentIntelligence


SYSTEM_PROMPT = """You normalize procurement intent for ASC. Return one JSON object only.
Required keys: product_query, quantity, max_budget_paise, currency,
max_delivery_days, hard_specs, preferences, recommended_strategies,
strategy_rationale, confidence. Money must be integer paise. recommended_strategies
may contain only DIRECT_MATCH, VOLUME_DISCOUNT, BUNDLE_OVERSTOCK,
PRODUCT_SUBSTITUTE, QUANTITY_ADJUSTMENT, or DELIVERY_TRADEOFF. You propose
strategies only; never invent a price, discount,
approval, policy result, or payment decision."""


class LLMProvider(ABC):
    name: str
    model: Optional[str]

    @abstractmethod
    def analyze(self, text: str) -> IntentIntelligence:
        raise NotImplementedError


class RuleBasedIntentProvider(LLMProvider):
    name = "deterministic"
    model = None

    _NUMBER_WORDS = {
        "one": 1, "five": 5, "ten": 10, "fifteen": 15, "twenty": 20,
        "twenty-five": 25, "thirty": 30, "forty": 40, "fifty": 50,
    }

    @classmethod
    def inspect_required_fields(cls, text: str) -> Dict[str, Any]:
        """Extract only explicitly supplied fields; never insert demo defaults."""
        lower = text.lower()
        product_query = cls._extract_product_optional(lower)
        quantity = cls._extract_quantity_optional(lower)
        budget_paise = cls._extract_budget_paise_optional(lower)
        values = {
            "product_query": product_query,
            "quantity": quantity,
            "max_budget_paise": budget_paise,
        }
        return {
            "known_fields": {key: value for key, value in values.items() if value is not None},
            "missing_fields": [key for key, value in values.items() if value is None],
        }

    def analyze(self, text: str) -> IntentIntelligence:
        lower = text.lower()
        quantity = self._extract_quantity(lower)
        budget_paise = self._extract_budget_paise(lower)

        product_query = self._extract_product_optional(lower) or "Lenovo IdeaPad"
        ram = self._first_int(lower, r"(?:at least|min(?:imum)?\s*)?(\d+)\s*gb\s*(?:ram|memory)")
        storage = self._first_int(lower, r"(?:at least|min(?:imum)?\s*)?(\d+)\s*gb\s*(?:ssd|storage)")
        cpu_match = re.search(r"\b(i[3579])\b", lower)
        delivery = self._first_int(lower, r"(?:within|delivery\s+(?:in|within))\s*(\d+)\s*days?")
        if delivery is None and ("within a week" in lower or "within one week" in lower):
            delivery = 7

        preferences = []
        if any(word in lower for word in ("alternative", "substitute", "either brand")):
            preferences.append("alternative_products_allowed")
        if any(word in lower for word in ("bundle", "accessor", "overstock")):
            preferences.append("bundles_preferred")
        if "non-negotiable" in lower and delivery:
            preferences.append("delivery_is_hard_constraint")

        strategies = [AllowedStrategy.VOLUME_DISCOUNT]
        if "bundles_preferred" in preferences:
            strategies.insert(0, AllowedStrategy.BUNDLE_OVERSTOCK)
        else:
            strategies.append(AllowedStrategy.BUNDLE_OVERSTOCK)
        if "alternative_products_allowed" in preferences or "laptop" in lower:
            strategies.append(AllowedStrategy.PRODUCT_SUBSTITUTE)
        if re.search(r"\b(?:around|approximately|about)\b", lower):
            strategies.append(AllowedStrategy.QUANTITY_ADJUSTMENT)
        if any(phrase in lower for phrase in ("delivery is flexible", "flexible delivery", "can wait")):
            strategies.append(AllowedStrategy.DELIVERY_TRADEOFF)

        return IntentIntelligence(
            product_query=product_query,
            quantity=quantity,
            max_budget_paise=budget_paise,
            max_delivery_days=delivery or 7,
            hard_specs=HardSpecifications(
                min_ram_gb=ram,
                min_cpu_tier=cpu_match.group(1) if cpu_match else None,
                min_storage_gb=storage,
            ),
            preferences=preferences,
            recommended_strategies=list(dict.fromkeys(strategies)),
            strategy_rationale="Explore only policy-supported deterministic offer strategies that can satisfy the stated constraints.",
            confidence=0.72,
            provider=self.name,
        )

    @classmethod
    def _extract_quantity(cls, text: str) -> int:
        return cls._extract_quantity_optional(text) or 20

    @classmethod
    def _extract_quantity_optional(cls, text: str) -> Optional[int]:
        match = re.search(r"(\d+)\s*(?:lenovo|hp|ideapad|thinkpad|laptops?|monitors?|mice|mouse|keyboards?|chairs?|units?|items?)", text)
        if match:
            return int(match.group(1))
        explicit = re.search(r"\bquantity\s*(?::|is|of)?\s*(\d+)\b", text)
        if explicit:
            return int(explicit.group(1))
        for word, value in cls._NUMBER_WORDS.items():
            if re.search(rf"\b{re.escape(word)}\s+(?:\w+\s+)?(?:laptops?|monitors?|mice|mouse|keyboards?|chairs?|units?|items?)\b", text):
                return value
        return None

    @staticmethod
    def _extract_budget_paise(text: str) -> int:
        return RuleBasedIntentProvider._extract_budget_paise_optional(text) or 250_000_000

    @staticmethod
    def _extract_budget_paise_optional(text: str) -> Optional[int]:
        pattern = r"(?:budget|max(?:imum)?(?:\s+total)?(?:\s+budget)?|up to|under)\s*(?:of|is)?\s*(?:roughly|about|around)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l|k|crore|cr)?"
        match = re.search(pattern, text)
        if not match:
            match = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l|k|crore|cr)?", text)
        if not match:
            return None
        value = float(match.group(1).replace(",", ""))
        unit = (match.group(2) or "").lower()
        multiplier = {
            "lakh": 100_000, "lakhs": 100_000, "l": 100_000,
            "k": 1_000, "crore": 10_000_000, "cr": 10_000_000,
        }.get(unit, 1)
        return int(value * multiplier * 100)

    @staticmethod
    def _extract_product_optional(text: str) -> Optional[str]:
        explicit = re.search(
            r"\b(?:product|item)\s*:\s*([a-z0-9][a-z0-9 '\-/]*?)(?=\s*\.|\s*,|\s+quantity\b|$)",
            text,
        )
        if explicit:
            return explicit.group(1).strip().title()
        if re.search(r"\b(?:mouse|mice)\b", text):
            return "Wireless Mouse"
        if "hp" in text and "monitor" in text:
            return "HP P24 G5 Monitor"
        if "monitor" in text:
            return "Monitor"
        if "thinkpad" in text:
            return "Lenovo ThinkPad"
        if "ideapad" in text:
            return "Lenovo IdeaPad"
        if "probook" in text or ("hp" in text and "laptop" in text):
            return "HP ProBook"
        if "lenovo" in text and "laptop" in text:
            return "Lenovo IdeaPad"
        if "laptop" in text:
            return "Laptop"
        if "keyboard" in text:
            return "Wireless Keyboard"
        if "chair" in text:
            return "Ergonomic Chair"
        return None

    @staticmethod
    def _first_int(text: str, pattern: str) -> Optional[int]:
        match = re.search(pattern, text)
        return int(match.group(1)) if match else None


class CloudLLMProvider(LLMProvider):
    """Configurable JSON-over-HTTP cloud provider using a chat-completions shape."""

    name = "cloud"

    def __init__(self, endpoint: str, api_key: str, model: str, timeout: float = 12.0):
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def analyze(self, text: str) -> IntentIntelligence:
        response = httpx.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return self._validate(content)

    def _validate(self, content: Any) -> IntentIntelligence:
        data = _json_object(content)
        result = IntentIntelligence.model_validate(data)
        return result.model_copy(
            update={"provider": self.name, "model": self.model, "fallback_reason": None}
        )


class GeminiFlashProvider(LLMProvider):
    """Google Gemini JSON provider for bounded intent and agent-language tasks."""

    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash", timeout: float = 20.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )

    def _generate(
        self,
        system_prompt: str,
        user_text: str,
        json_mode: bool = False,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        generation_config: Dict[str, Any] = {"temperature": 0.1}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"
        if response_schema:
            generation_config["responseJsonSchema"] = response_schema
        request_body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": generation_config,
        }
        response = None
        for attempt in range(3):
            response = httpx.post(
                self.endpoint,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=request_body,
                timeout=self.timeout,
            )
            if response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                break
            time.sleep(1.5 * (attempt + 1))
        assert response is not None
        response.raise_for_status()
        payload = response.json()
        return "".join(
            part.get("text", "")
            for part in payload["candidates"][0]["content"]["parts"]
        ).strip()

    def analyze(self, text: str) -> IntentIntelligence:
        result = IntentIntelligence.model_validate(
            _json_object(
                self._generate(
                    SYSTEM_PROMPT,
                    text,
                    json_mode=True,
                    response_schema=IntentIntelligence.model_json_schema(),
                )
            )
        )
        return result.model_copy(
            update={"provider": self.name, "model": self.model, "fallback_reason": None}
        )

    def inspect_required_fields(self, text: str) -> Dict[str, Any]:
        prompt = """Extract only procurement fields explicitly stated or unambiguously implied.
Return JSON with product_query, quantity, and max_budget_paise. Use null for every
missing field. Never guess defaults. max_budget_paise must be an integer number of
Indian paise. Return JSON only."""
        data = _json_object(
            self._generate(
                prompt,
                text,
                json_mode=True,
                response_schema={
                    "type": "object",
                    "properties": {
                        "product_query": {"type": ["string", "null"]},
                        "quantity": {"type": ["integer", "null"]},
                        "max_budget_paise": {"type": ["integer", "null"]},
                    },
                    "required": ["product_query", "quantity", "max_budget_paise"],
                    "additionalProperties": False,
                },
            )
        )
        known: Dict[str, Any] = {}
        product = data.get("product_query")
        quantity = data.get("quantity")
        budget = data.get("max_budget_paise")
        if isinstance(product, str) and product.strip():
            known["product_query"] = product.strip()
        if isinstance(quantity, int) and quantity > 0:
            known["quantity"] = quantity
        if isinstance(budget, int) and budget > 0:
            known["max_budget_paise"] = budget
        required = ["product_query", "quantity", "max_budget_paise"]
        return {"known_fields": known, "missing_fields": [field for field in required if field not in known]}

    def compose_merchant_reply(self, facts: Dict[str, Any]) -> str:
        prompt = """You are the Merchant Agent in a procurement negotiation. Write a concise,
professional reply to the Buyer Agent using only the supplied deterministic facts.
Do not change numbers, invent products, promise approval, or hide a failure. State
whether inventory exists, why the offer succeeded or failed, and the practical next
steps. Return plain text only, no markdown."""
        return self._generate(prompt, json.dumps(facts, ensure_ascii=False), json_mode=False)


class OllamaLLMProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 20.0):
        self.endpoint = f"{base_url.rstrip('/')}/api/chat"
        self.model = model
        self.timeout = timeout

    def analyze(self, text: str) -> IntentIntelligence:
        response = httpx.post(
            self.endpoint,
            json={
                "model": self.model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = _json_object(response.json()["message"]["content"])
        result = IntentIntelligence.model_validate(data)
        return result.model_copy(
            update={"provider": self.name, "model": self.model, "fallback_reason": None}
        )


def _json_object(content: Any) -> Dict[str, Any]:
    if isinstance(content, dict):
        return content
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(content).strip(), flags=re.IGNORECASE)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Provider response must be a JSON object")
    return value
