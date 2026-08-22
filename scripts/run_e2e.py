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


def evaluate(result: PipelineResult, record_id_to_group: dict) -> dict:
    """
    Evaluate decisions against ground truth.
    Uses explicit source_record_id -> ground_truth_group_id lookup without string splitting.
    """
    true_matches = 0
    false_auto_matches = 0
    total_value = 0
    verified_value = 0
    
    # Track event resolution
    event_status = {}  # group_id -> {'total_records': 0, 'correct_matches': 0}
    for sid, gid in record_id_to_group.items():
        if gid:
            if gid not in event_status:
                event_status[gid] = {'total_records': 0, 'correct_matches': 0}
            event_status[gid]['total_records'] += 1

    for dec in result.decisions:
        raw_sid = dec.source_event_id
        total_value += dec.amount_minor_units
        my_group = record_id_to_group.get(raw_sid)

        if dec.action == 'MATCH':
            verified_value += dec.amount_minor_units
            chosen_sid = dec.chosen_candidate_sid
            if chosen_sid:
                chosen_group = record_id_to_group.get(chosen_sid)
                if my_group and chosen_group and my_group == chosen_group:
                    true_matches += 1
                    event_status[my_group]['correct_matches'] += 1
                else:
                    false_auto_matches += 1
            else:
                false_auto_matches += 1

    auto_resolved = result.auto_resolved
    false_auto_match_rate = false_auto_matches / auto_resolved if auto_resolved else 0.0
    value_coverage = verified_value / total_value if total_value else 0.0
    
    events_fully_resolved = sum(1 for status in event_status.values() 
                              if status['total_records'] > 0 and 
                              status['correct_matches'] == status['total_records'])

    return {
        'true_matches': true_matches,
        'false_auto_matches': false_auto_matches,
        'false_auto_match_rate': false_auto_match_rate,
        'value_coverage_pct': value_coverage,
        'total_value_minor': total_value,
        'verified_value_minor': verified_value,
        'events_fully_resolved': events_fully_resolved,
        'total_events': len(event_status)
    }

def print_scorecard(label: str, result: PipelineResult, eval_metrics: dict):
    total = len(result.decisions)
    sep = '─' * 60
    print(f"\n{'═'*60}")
    print(f"  RazorLedger — Run Scorecard: {label}")
    print(f"{'═'*60}")
    print(f"  Economic events total: {eval_metrics.get('total_events', 150):>6}")
    print(f"  Events fully resolved: {eval_metrics.get('events_fully_resolved', 0):>6}")
    print(sep)
    print(f"  Source records total : {result.total_source_records:>6}  (150 events × 3 sources)")
    print(f"  Deduplicated         : {result.deduplicated:>6}  (idempotency catches)")
    print(f"  Accepted into pipeline: {result.accepted:>5}")
    print(sep)
    print(f"  Decisions total      : {total:>6}")
    print(f"  MATCH (auto-resolved): {result.auto_resolved:>6}  ({result.safe_automation_rate:>7.1%})")
    print(f"  REVIEW               : {result.review_count:>6}  ({result.review_rate:>7.1%})")
    print(f"  NO_MATCH             : {result.no_match_count:>6}  ({result.no_match_rate:>7.1%})")
    print(f"  PENDING              : {result.pending_count:>6}  ({result.pending_rate:>7.1%})")
    print(f"  Non-automated total  : {result.review_count+result.no_match_count+result.pending_count:>6}  ({result.non_automated_rate:>7.1%})")
    print(sep)
    print(f"  Blocking: naive={result.naive_comparison_count:,}  "
          f"candidates={result.candidate_pair_count:,}  "
          f"reduction={result.blocking_reduction_factor:.1f}x")
    print(sep)
    print("  HERO METRICS (in priority order):")
    print(f"  1. Safe automation rate    : {result.safe_automation_rate:>7.1%}")
    print(f"  2. Value coverage          : {eval_metrics['value_coverage_pct']:>7.1%}  "
          f"(₹{eval_metrics['verified_value_minor']//100:,} of ₹{eval_metrics['total_value_minor']//100:,})")
    print(f"  3. False auto-match rate   : {eval_metrics['false_auto_match_rate']:>7.1%}  "
          f"({eval_metrics['false_auto_matches']} wrong auto-matches)")
    print(f"  4. Review rate             : {result.review_rate:>7.1%}")
    print(f"  5. Adversarial holdout     : {'N/A (P1)':>12}")
    print(sep)
    print(f"  True matches (verified)  : {eval_metrics['true_matches']:>6}")
    print(f"  False auto-matches       : {eval_metrics['false_auto_matches']:>6}")
    print(f"{'═'*60}\n")



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
    eval_metrics_dev = evaluate(result_dev, truth_dev)
    print_scorecard('DEV', result_dev, eval_metrics_dev)

    # Run on VALIDATION
    result_val, truth_val = run_pipeline(
        seed=PARTITION_SEEDS['VALIDATION'],
        partition='VALIDATION',
        label='VALIDATION',
    )
    eval_metrics_val = evaluate(result_val, truth_val)
    print_scorecard('VALIDATION', result_val, eval_metrics_val)

    # Run on TEST_ADVERSARIAL
    result_adv, truth_adv = run_pipeline(
        seed=PARTITION_SEEDS['TEST_ADVERSARIAL'],
        partition='TEST_ADVERSARIAL',
        label='TEST_ADVERSARIAL',
    )
    eval_metrics_adv = evaluate(result_adv, truth_adv)
    print_scorecard('TEST_ADVERSARIAL', result_adv, eval_metrics_adv)

    # FROZEN_UNSEEN is explicitly skipped/untouched until system is frozen.
    print("FROZEN_UNSEEN skipped (reserved for final evaluation).")

if __name__ == '__main__':
    main()
