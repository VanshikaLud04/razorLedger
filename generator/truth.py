"""
generator/truth.py — EVALUATOR ONLY.

This module may ONLY be imported by evaluation/. It must NEVER be imported by app/.
The test suite enforces this boundary (see tests/test_benchmark_integrity.py).

ground_truth_group_id maps each opaque per-source source_event_id back to the
underlying economic event. The matcher never sees this mapping.
"""
from dataclasses import dataclass, field


@dataclass
class GroundTruthRecord:
    """
    Evaluator-only record. Never enters the matching pipeline.
    Produced alongside source records but written to a separate file/store
    that app/ code has no import path to.
    """
    ground_truth_group_id: str       # e.g. "GRP-00042"
    economic_event_id: str           # internal generator ID — evaluator use only
    source: str                      # BANK / INVOICE / GATEWAY
    source_event_id: str             # opaque ID given to the matcher
    is_control_conflict: bool = False
    is_duplicate_delivery: bool = False
    is_partial: bool = False


@dataclass
class GroundTruthBundle:
    """All truth records for one reconciliation run."""
    records: list[GroundTruthRecord] = field(default_factory=list)

    def group_ids_for_event(self, economic_event_id: str) -> list[str]:
        """Return all source_event_ids that share an economic_event_id."""
        return [r.source_event_id for r in self.records
                if r.economic_event_id == economic_event_id]

    def group_for_source_event(self, source_event_id: str) -> str | None:
        """Return ground_truth_group_id for a given source_event_id."""
        for r in self.records:
            if r.source_event_id == source_event_id:
                return r.ground_truth_group_id
        return None

    def source_events_in_group(self, ground_truth_group_id: str) -> list[str]:
        """Return all source_event_ids belonging to the same economic event."""
        return [r.source_event_id for r in self.records
                if r.ground_truth_group_id == ground_truth_group_id]
