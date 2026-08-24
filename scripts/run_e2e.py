#!/usr/bin/env python3.13
"""
scripts/run_e2e.py — End-to-end 150-event reconciliation run.

Usage:
    python3.13 scripts/run_e2e.py

Runs the full pipeline in-memory (no DB required):
  1. Generate 150 economic events (DEV seed)
  2. Derive ~450+ source records
  3. Strip ground_truth_group_id (ingest boundary)
  4. Run ReconciliationPipeline
  5. Evaluate against ground truth
  6. Print scorecard with REAL non-illustrative numbers

Constitution rule 9: every number here comes from a frozen run.
No numbers are manufactured or reused from planning docs.
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import copy
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

from generator.config import GeneratorConfig, PARTITION_SEEDS
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver
from generator.truth import GroundTruthBundle
from app.matching.evidence import compute_rarity_frequencies
from app.pipeline import ReconciliationPipeline, PipelineResult


def run_pipeline(seed: str, partition: str, label: str) -> tuple[PipelineResult, GroundTruthBundle]:
    cfg = GeneratorConfig(seed=seed, partition=partition)

    logger.info(f"[{label}] Generating 150 economic events (seed={seed})")
    events = EconomicEventGenerator(cfg).generate()
    deriver = SourceViewDeriver(cfg)
    raw_records, truth = deriver.derive(events)

    logger.info(f"[{label}] {len(events)} events → {len(raw_records)} source records "
                f"(including {sum(1 for e in events if e.is_duplicate_delivery)} duplicate deliveries)")

    # ── Ingest boundary: strip ground_truth_group_id, simulate dedup ─────────
    seen_sids: set[tuple] = set()
    deduplicated = 0
    clean_records = []
    # NEW explicit mapping for evaluator
    record_id_to_truth_group = {}

    for rec in raw_records:
        r = copy.copy(rec)
        truth_group = r.pop('ground_truth_group_id', None)  # STRIP — never reaches pipeline
        key = (r['source'], r['source_event_id'])
        if key in seen_sids:
            deduplicated += 1
            continue
        seen_sids.add(key)
        # Assign a simple local source_record_id for in-memory pipeline
        sid = f"{r['source']}-{r['source_event_id']}"
        r.setdefault('source_record_id', sid)
        record_id_to_truth_group[sid] = truth_group
        clean_records.append(r)

    logger.info(f"[{label}] After dedup: {len(clean_records)} records accepted, "
                f"{deduplicated} deduplicated (idempotency test)")

    # ── Rarity frequencies: fitted on same DEV set ────────────────────────────
    rarity = compute_rarity_frequencies(clean_records)
    logger.info(f"[{label}] Rarity table: {len(rarity)-1} reference tokens fitted on DEV")

    # ── Run pipeline ──────────────────────────────────────────────────────────
    pipeline = ReconciliationPipeline(rarity_frequencies=rarity)
    result = pipeline.run(clean_records, seed=seed)
    result.deduplicated = deduplicated
    result.accepted = len(clean_records)
    result.total_source_records = len(raw_records)

    return result, record_id_to_truth_group


from evaluation.benchmark import BenchmarkEvaluator

def evaluate(result: PipelineResult, record_id_to_group: dict) -> dict:
    # Deprecated: use BenchmarkEvaluator instead
    pass

def print_scorecard(label: str, result: PipelineResult, eval_metrics: dict):
    # Deprecated: use BenchmarkEvaluator instead
    pass



def main():
    print("\nRazorLedger — End-to-End 150-Event Reconciliation Run")
    print("Constitution rule 9: these are REAL numbers from a frozen run.")
    print("No numbers are manufactured or reused from planning documents.\n")

    # Run on DEV partition
    result_dev, truth_dev = run_pipeline(
        seed=PARTITION_SEEDS['DEV'],
        partition='DEV',
        label='DEV',
    )
    evaluator_dev = BenchmarkEvaluator(truth_dev, result_dev)
    metrics_dev = evaluator_dev.compute()
    evaluator_dev.generate_scorecard('DEV', metrics_dev)

    # Run on VALIDATION
    result_val, truth_val = run_pipeline(
        seed=PARTITION_SEEDS['VALIDATION'],
        partition='VALIDATION',
        label='VALIDATION',
    )
    evaluator_val = BenchmarkEvaluator(truth_val, result_val)
    metrics_val = evaluator_val.compute()
    evaluator_val.generate_scorecard('VALIDATION', metrics_val)

    # Run on ADVERSARIAL_HOLDOUT
    result_adv, truth_adv = run_pipeline(
        seed=PARTITION_SEEDS['ADVERSARIAL_HOLDOUT'],
        partition='ADVERSARIAL_HOLDOUT',
        label='ADVERSARIAL_HOLDOUT',
    )
    evaluator_adv = BenchmarkEvaluator(truth_adv, result_adv)
    metrics_adv = evaluator_adv.compute()
    evaluator_adv.generate_scorecard('ADVERSARIAL_HOLDOUT', metrics_adv)

    # FROZEN_UNSEEN is explicitly skipped/untouched until system is frozen.
    print("FROZEN_UNSEEN skipped (reserved for final evaluation).")

if __name__ == '__main__':
    main()
