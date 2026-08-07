"""Pure scoring function for Phase 7 strategy evaluation.

Turns a `ResearchQualityResult` (already computed by `src/quality/validator.py`
from real sources/evidence/claims) into a single comparable number. Never
invents a metric that isn't derivable from the quality result itself.
"""

from src.quality.models import ResearchQualityResult


def score_quality_result(quality: ResearchQualityResult) -> float:
    return (
        2.0 * quality.supported_claim_count
        - 1.5 * quality.contradicted_claim_count
        - 1.0 * quality.unverified_claim_count
        - 0.5 * quality.unsupported_claim_count
        + 0.5 * quality.unique_source_count
        - 3.0 * len(quality.errors)
        - 1.0 * len(quality.warnings)
        + (5.0 if quality.valid else 0.0)
    )
