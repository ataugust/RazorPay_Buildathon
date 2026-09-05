"""Selects the configured provider and guarantees a deterministic fallback."""

import os

from app.core import config as _config  # Loads backend/.env before provider selection.
from app.llm.contracts import IntentIntelligence
from app.llm.providers import (
    CloudLLMProvider,
    GeminiFlashProvider,
    LLMProvider,
    OllamaLLMProvider,
    RuleBasedIntentProvider,
)


class IntentIntelligenceService:
    def __init__(self, provider: LLMProvider | None = None):
        self.fallback = RuleBasedIntentProvider()
        self.provider = provider or self._configured_provider()

    def analyze(self, text: str) -> IntentIntelligence:
        try:
            result = self.provider.analyze(text)
            baseline = self.fallback.analyze(text)
            strategies = list(dict.fromkeys([
                *result.recommended_strategies,
                *baseline.recommended_strategies,
            ]))
            return result.model_copy(update={"recommended_strategies": strategies})
        except Exception as exc:
            fallback = self.fallback.analyze(text)
            return fallback.model_copy(
                update={
                    "provider": "deterministic_fallback",
                    "fallback_reason": f"{type(exc).__name__}: configured intelligence provider unavailable or invalid",
                }
            )

    @staticmethod
    def _configured_provider() -> LLMProvider:
        provider = os.getenv("ASC_LLM_PROVIDER", "deterministic").strip().lower()
        timeout = float(os.getenv("ASC_LLM_TIMEOUT_SECONDS", "12"))
        if provider == "cloud":
            endpoint = os.getenv("ASC_LLM_ENDPOINT", "").strip()
            api_key = os.getenv("ASC_LLM_API_KEY", "").strip()
            model = os.getenv("ASC_LLM_MODEL", "").strip()
            if endpoint and api_key and model:
                return CloudLLMProvider(endpoint, api_key, model, timeout)
        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if api_key:
                return GeminiFlashProvider(
                    api_key,
                    os.getenv("ASC_LLM_MODEL", "gemini-3.5-flash").strip() or "gemini-3.5-flash",
                    timeout,
                )
        elif provider == "ollama":
            return OllamaLLMProvider(
                os.getenv("ASC_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                os.getenv("ASC_LLM_MODEL", "llama3.1:8b"),
                timeout,
            )
        return RuleBasedIntentProvider()


class AgentLanguageService:
    """Uses Gemini for language only and preserves deterministic facts on fallback."""

    def __init__(self):
        self.provider = IntentIntelligenceService._configured_provider()

    def inspect_required_fields(self, text: str):
        deterministic = RuleBasedIntentProvider.inspect_required_fields(text)
        if not deterministic["missing_fields"]:
            return deterministic
        if isinstance(self.provider, GeminiFlashProvider):
            try:
                return self.provider.inspect_required_fields(text)
            except Exception:
                pass
        return deterministic

    def compose_merchant_reply(self, facts: dict) -> tuple[str, str, str | None]:
        fallback = str(facts["message"])
        if isinstance(self.provider, GeminiFlashProvider):
            try:
                return self.provider.compose_merchant_reply(facts), self.provider.name, self.provider.model
            except Exception:
                return fallback, "deterministic_fallback", self.provider.model
        return fallback, "deterministic", None
