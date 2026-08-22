"""
app/matching/probabilistic.py — Fellegi-Sunter inspired probabilistic scorer.

Re-exports EvidenceWeightedScorer as ProbabilisticScorer for canonical naming.
All scoring logic lives in evidence_weighted.py; this is the import contract.

Key rules (enforced in check_auto_match_eligibility):
  - Auto-match requires confidence >= auto_match_threshold (default 0.80)
  - Auto-match requires confidence_gap_to_next >= minimum_confidence_gap (default 0.10)
  - Auto-match requires >= 2 distinct evidence families (NUMERIC/TEMPORAL/IDENTITY/SEMANTIC/SOURCE)
  - Auto-match requires source_compatibility == True
  - LLM adjustment is bounded by llm_max_evidence_delta (config, tune on DEV only)
  - LLM cannot independently push a candidate over the auto-match threshold
    unless all non-LLM requirements are already satisfied.
"""

from app.matching.evidence_weighted import EvidenceWeightedScorer

# Canonical name used by all other modules
ProbabilisticScorer = EvidenceWeightedScorer

__all__ = ['ProbabilisticScorer']
