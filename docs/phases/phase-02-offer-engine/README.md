# Phase 2 — Deterministic Offer Engine

## Status

Implemented and regression-tested on 2026-09-04.

## Responsibilities

- Load the active merchant policy and catalog
- Generate volume-discount, overstock-bundle, and product-substitution candidates
- Calculate integer commercial values in Python
- Score candidates using merchant-controlled weights
- Give candidates below the margin floor a score of zero
- Pass the winning candidate to Phase 3

## Authoritative files

- `backend/app/asc/orchestrator.py`
- `backend/app/asc/candidate_generators.py`
- `backend/app/asc/scoring_engine.py`
- `backend/app/domain/strategy_types.py`
- `backend/app/db/models/merchant_policy.py`

## Validation

`python -m scripts.test_phase2` generated and ranked all three strategies. The verified winner for the reference case was `VOLUME_DISCOUNT` at Rs. 2,400,000, 16.67% margin, and score 36.27.

