import copy
import json
from pathlib import Path

from app.pipeline import ReconciliationPipeline, load_config
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver
from generator.config import GeneratorConfig
from app.matching.evidence import compute_rarity_frequencies
from evaluation.benchmark import BenchmarkEvaluator

def main():
    base_config = load_config()
    seed = 'razorledger-dev-v1'
    cfg = GeneratorConfig(seed=seed, partition='DEV')
    events = EconomicEventGenerator(cfg).generate()
    raw_records, truth = SourceViewDeriver(cfg).derive(events)

    clean_records = []
    seen = set()
    record_id_to_truth_group = {}
    for rec in raw_records:
        r = copy.copy(rec)
        truth_group = r.pop('ground_truth_group_id', None)
        key = (r['source'], r['source_event_id'])
        if key in seen:
            continue
        seen.add(key)
        r['source_record_id'] = f"{r['source']}-{r['source_event_id']}"
        record_id_to_truth_group[r['source_record_id']] = truth_group
        clean_records.append(r)

    rarity = compute_rarity_frequencies(clean_records)

    # Capture allocator output via monkeypatch, without touching pipeline.py's
    # own logic (item 8: no architecture changes beyond the targeted fix).
    from app.matching.allocator import OneToNAllocator
    captured_groups = []
    original_group_and_validate = OneToNAllocator.group_and_validate
    def _capturing_group_and_validate(self, scored_records):
        result = original_group_and_validate(self, scored_records)
        captured_groups.extend(result)
        return result
    OneToNAllocator.group_and_validate = _capturing_group_and_validate

    pipe = ReconciliationPipeline(config=copy.deepcopy(base_config), rarity_frequencies=rarity, disabled_stages={'E_LLM'})
    res = pipe.run(copy.deepcopy(clean_records), seed=seed)

    OneToNAllocator.group_and_validate = original_group_and_validate

    # Count 3-way groups the allocator actually accepted, for the "records lost" report
    three_way_count = 0
    three_way_record_count = 0
    cardinality_breakdown = {}
    for group in captured_groups:
        sources = [r.get('source') for r in group]
        key = tuple(sorted(f"{s}x{sources.count(s)}" for s in set(sources)))
        cardinality_breakdown[key] = cardinality_breakdown.get(key, 0) + 1
        if sources.count('BANK') == 1 and sources.count('GATEWAY') == 1 and sources.count('INVOICE') == 1:
            three_way_count += 1
            three_way_record_count += 3

    eval_run = BenchmarkEvaluator(record_id_to_truth_group, res)
    eval_res = eval_run.compute()
    m = eval_res.metrics
    raw = eval_res.raw_metrics

    result = {
        'partition': 'DEV',
        'records': len(clean_records),
        'MATCH': raw.get('auto_resolved', 0),
        'REVIEW': raw.get('review_count', 0),
        'PENDING': raw.get('pending_count', 0),
        'NO_MATCH': raw.get('no_match_count', 0),
        'safe_automation_pct': m.get('safe_automation_rate', 0.0),
        'value_coverage_pct': m.get('value_coverage_pct', 0.0),
        'precision': m.get('precision', 0.0),
        'recall': m.get('recall', 0.0),
        'false_auto_match_pct': m.get('false_auto_match_rate', 0.0),
        'three_way_groups_accepted': three_way_count,
        'three_way_records_in_groups': three_way_record_count,
        'all_accepted_groups_by_cardinality': {str(k): v for k, v in cardinality_breakdown.items()},
        'total_accepted_groups': len(captured_groups),
    }
    print(json.dumps(result, indent=2))

    # Compare against the previously reported FINAL_SCORECARD DEV row, not FROZEN_UNSEEN
    prev_path = Path('reports/final/FINAL_SCORECARD.json')
    if prev_path.exists():
        prev = json.loads(prev_path.read_text())
        prev_dev = next((r for r in prev['partitions'] if r['partition'] == 'DEV'), None)
        if prev_dev:
            print("\n--- DELTA vs previous DEV result (0.50-threshold version) ---")
            print(f"MATCH: {prev_dev['MATCH']} -> {result['MATCH']} ({result['MATCH'] - prev_dev['MATCH']:+d})")
            print(f"Safe Automation: {prev_dev['safe_automation_pct']:.4f} -> {result['safe_automation_pct']:.4f} "
                  f"({result['safe_automation_pct'] - prev_dev['safe_automation_pct']:+.4f})")
            print(f"Value Coverage: {prev_dev['value_coverage_pct']:.4f} -> {result['value_coverage_pct']:.4f} "
                  f"({result['value_coverage_pct'] - prev_dev['value_coverage_pct']:+.4f})")
            print(f"False Auto-Match: {prev_dev['false_auto_match_pct']:.4f} -> {result['false_auto_match_pct']:.4f}")

if __name__ == "__main__":
    main()
