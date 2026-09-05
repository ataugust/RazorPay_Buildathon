"""Deprecated Phase 1 candidate-generator module.

Use ``app.asc.candidate_generators`` for the current SQLAlchemy-backed volume,
bundle, and substitution generators. This module contains no database access.
"""


class _RemovedLegacyAPI:
    def __init__(self, *_args, **_kwargs):
        raise RuntimeError(
            "Legacy candidate generator removed. Use app.asc.candidate_generators."
        )


StrategyGenerator = _RemovedLegacyAPI
CandidateGenerator = _RemovedLegacyAPI

__all__ = ["StrategyGenerator", "CandidateGenerator"]

