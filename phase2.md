# Phase 2 — Merchant Policy and Offer Engine

## Purpose

Rescue failed catalog matches by generating bounded offers and ranking them deterministically. No LLM is required.

## Status

**Core implementation present.** Source matches the intended design; the supplied script was not rerun because the checked-in virtual environment is machine-specific.

## Flow

```text
BuyerRequest
→ catalog/inventory lookup
→ direct-match feasibility check
→ candidate generation
→ deterministic ranking
→ winner sent to Phase 3
```

## Source map

| Concern | Source |
| --- | --- |
| Orchestrator | `backend/app/asc/orchestrator.py` |
| Generators | `backend/app/asc/candidate_generators.py` |
| Scoring | `backend/app/asc/scoring_engine.py` |
| Candidate contracts | `backend/app/domain/strategy_types.py` |
| Policy model | `backend/app/db/models/merchant_policy.py` |
| Verification | `backend/scripts/test_phase2.py` |

## Strategies

- **Volume discount:** approaches the buyer budget without exceeding the policy discount cap.
- **Overstock bundle:** combines the requested product with stocked overstock when bundles are allowed.
- **Product substitute:** selects an active same-category product that fits budget and stock constraints.

All candidates contain explicit line-item prices, costs, totals, margins, and discounts calculated in Python.

## Policy defaults

- Minimum margin: 15%
- Maximum discount: 20%
- Bundles and substitutions: enabled
- Weights: margin 0.4, revenue 0.3, overstock 0.2, discount penalty 0.1

## Scoring

```text
score = margin_weight × normalized_margin
      + revenue_weight × normalized_revenue
      + overstock_weight × overstock_ratio
      - discount_weight × normalized_discount
```

Candidates below the minimum margin receive a final score of zero.

## Money boundary

- Request budget: integer paise.
- Orchestrator converts to integer rupees with `// 100`.
- Candidates use integer rupees.
- Approved response total is converted back to paise.

## Known gaps

- No explicit direct-match candidate exists in the active orchestrator. When catalog price already fits, the volume generator returns `None`; the other generators may still determine the result.
- The verification script prints results but has no assertions.
- Edge cases for zero quantity, negative budgets, rounding, ties, and invalid weights lack automated coverage.

## Completion criteria

- Implement and test a direct-match candidate path.
- Convert Phase 2 verification to assertion-based tests.
- Add edge-case coverage.
- Run against a clean migrated and seeded database.

