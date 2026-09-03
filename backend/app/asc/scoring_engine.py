from typing import List, Tuple
from pydantic import BaseModel
from app.db.models.merchant_policy import MerchantPolicy
from app.domain.strategy_types import OfferCandidate

class ScoredOffer(BaseModel):
    candidate: OfferCandidate
    final_score: float
    margin_score: float
    revenue_score: float
    overstock_score: float
    discount_penalty: float
    passes_min_margin: bool

class DeterministicScoringEngine:
    """Ranks candidate offers using a deterministic objective scoring function."""

    @staticmethod
    def score_candidate(candidate: OfferCandidate, max_budget_rupees: int, policy: MerchantPolicy) -> ScoredOffer:
        # Check minimum margin floor
        passes_margin = candidate.margin_percent >= policy.min_margin_percent

        # Normalized component scores (0.0 to 1.0)
        margin_score = min(1.0, max(0.0, candidate.margin_percent / 100.0))
        revenue_score = min(1.0, max(0.0, candidate.total_price_rupees / max_budget_rupees)) if max_budget_rupees > 0 else 0.0
        overstock_score = candidate.overstock_ratio
        discount_penalty = min(1.0, max(0.0, candidate.discount_percent / 100.0))

        # Weighted Objective Calculation
        raw_score = (
            (policy.weight_margin * margin_score) +
            (policy.weight_revenue * revenue_score) +
            (policy.weight_overstock * overstock_score) -
            (policy.weight_discount_penalty * discount_penalty)
        )

        # Scale to 0-100 for intuitive display
        final_score = round(max(0.0, raw_score) * 100, 2)

        return ScoredOffer(
            candidate=candidate,
            final_score=final_score if passes_margin else 0.0, # Zero score if margin floor fails
            margin_score=round(margin_score * 100, 2),
            revenue_score=round(revenue_score * 100, 2),
            overstock_score=round(overstock_score * 100, 2),
            discount_penalty=round(discount_penalty * 100, 2),
            passes_min_margin=passes_margin
        )

    @classmethod
    def rank_candidates(
        cls, 
        candidates: List[OfferCandidate], 
        max_budget_rupees: int, 
        policy: MerchantPolicy
    ) -> List[ScoredOffer]:
        scored_list = [
            cls.score_candidate(cand, max_budget_rupees, policy) 
            for cand in candidates
        ]
        # Sort by final score descending
        return sorted(scored_list, key=lambda s: s.final_score, reverse=True)
