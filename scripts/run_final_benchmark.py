import copy
import csv
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, UTC

from app.pipeline import ReconciliationPipeline, load_config
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver
from generator.config import GeneratorConfig
from app.matching.evidence import compute_rarity_frequencies
from evaluation.benchmark import BenchmarkEvaluator

def get_git_info():
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
        status = subprocess.check_output(['git', 'status', '--short']).decode().strip()
        return {'commit': commit, 'clean': not bool(status)}
    except:
        return {'commit': 'unknown', 'clean': False}

def main():
    base_config = load_config()
    out_dir = Path("reports/final")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    rows = []
    
    # 1. Run Baseline (Original P1) - Just Stage A (Deterministic) on DEV for Delta Table
    # The original baseline was ~15.1% on DEV.
    seed_dev = 'razorledger-dev-v1'
    cfg_dev = GeneratorConfig(seed=seed_dev, partition='DEV')
    events_dev = EconomicEventGenerator(cfg_dev).generate()
    raw_records_dev, truth_dev = SourceViewDeriver(cfg_dev).derive(events_dev)
    clean_records_dev = []
    seen = set()
    record_id_to_truth_group_dev = {}
    for rec in raw_records_dev:
        r = copy.copy(rec)
        truth_group = r.pop('ground_truth_group_id', None)
        key = (r['source'], r['source_event_id'])
        if key in seen: continue
        seen.add(key)
        r['source_record_id'] = f"{r['source']}-{r['source_event_id']}"
        record_id_to_truth_group_dev[r['source_record_id']] = truth_group
        clean_records_dev.append(r)
    rarity_dev = compute_rarity_frequencies(clean_records_dev)
    
    # Run Baseline (Stages A-F, but A was the only one that worked well enough without thresholds breaking it in P1, wait, actually P1 Baseline was just the pipeline before any tuning, which got 15.1%. Let's just run the pipeline with B,C,D,E disabled to simulate "Original Deterministic Pipeline")
    base_pipe_config = copy.deepcopy(base_config)
    base_pipe_config['matching']['disabled_stages'] = ['B_FUZZY', 'C_SEMANTIC', 'D_EVIDENCE', 'E_LLM']
    base_pipe_config['matching']['auto_match_threshold'] = 0.95
    if 'allocation' not in base_pipe_config:
        base_pipe_config['allocation'] = {}
    base_pipe_config['allocation']['auto_match_threshold'] = 0.95
    pipe_baseline = ReconciliationPipeline(config=base_pipe_config, rarity_frequencies=rarity_dev)
    res_baseline = pipe_baseline.run(copy.deepcopy(clean_records_dev), seed=seed_dev)
    eval_baseline = BenchmarkEvaluator(record_id_to_truth_group_dev, res_baseline).compute()
    m_base = eval_baseline.metrics
    raw_base = eval_baseline.raw_metrics

    # 2. Run Final Fully Integrated Pipeline
    for partition in ['DEV', 'VALIDATION', 'TEST_ADVERSARIAL', 'FROZEN_UNSEEN']:
        seed = f'razorledger-{partition.lower()}-v1'
        cfg = GeneratorConfig(seed=seed, partition=partition)
        events = EconomicEventGenerator(cfg).generate()
        raw_records, truth = SourceViewDeriver(cfg).derive(events)
        
        clean_records = []
        seen = set()
        record_id_to_truth_group = {}
        for rec in raw_records:
            r = copy.copy(rec)
            truth_group = r.pop('ground_truth_group_id', None)
            key = (r['source'], r['source_event_id'])
            if key in seen: continue
            seen.add(key)
            r['source_record_id'] = f"{r['source']}-{r['source_event_id']}"
            record_id_to_truth_group[r['source_record_id']] = truth_group
            clean_records.append(r)
            
        rarity = compute_rarity_frequencies(clean_records)
        
        # FINAL RUN
        pipe = ReconciliationPipeline(config=copy.deepcopy(base_config), rarity_frequencies=rarity, disabled_stages={'E_LLM'})
        res = pipe.run(copy.deepcopy(clean_records), seed=seed)
        
        eval_run = BenchmarkEvaluator(record_id_to_truth_group, res)
        eval_res = eval_run.compute()
        m = eval_res.metrics
        raw = eval_res.raw_metrics
        
        # Verify Safety!
        assert m.get('false_auto_match_rate', 0.0) == 0.0, f"SAFETY VIOLATION IN {partition}! False auto-matches detected!"
        assert m.get('precision', 0.0) == 1.0, f"PRECISION VIOLATION IN {partition}!"
        
        row = {
            'partition': partition,
            'records': len(clean_records),
            'MATCH': raw.get('auto_resolved', 0),
            'REVIEW': raw.get('review_count', 0),
            'PENDING': raw.get('pending_count', 0),
            'NO_MATCH': raw.get('no_match_count', 0),
            'safe_automation_pct': m.get('safe_automation_rate', 0.0),
            'value_coverage_pct': m.get('value_coverage_pct', 0.0),
            'precision': m.get('precision', 0.0),
            'recall': m.get('recall', 0.0),
            'F1': m.get('f1', 0.0),
            'false_auto_match_pct': m.get('false_auto_match_rate', 0.0),
            'control_failures': raw.get('review_count', 0),
        }
        rows.append(row)

    # Output FINAL_SCORECARD.csv and FINAL_CROSS_PARTITION.csv
    with open(out_dir / "FINAL_CROSS_PARTITION.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    
    with open(out_dir / "FINAL_SCORECARD.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with open(out_dir / "FINAL_SCORECARD.json", "w") as f:
        json.dump({"partitions": rows}, f, indent=2)

    # 3. Output FINAL_DELTA_TABLE.csv
    final_dev = next(r for r in rows if r['partition'] == 'DEV')
    delta_rows = [
        {
            'Metric': 'MATCH count',
            'Original_P1': 68,
            'Final_P7': final_dev['MATCH'],
            'Absolute_Delta': final_dev['MATCH'] - 68
        },
        {
            'Metric': 'Safe Automation %',
            'Original_P1': 0.1511,
            'Final_P7': final_dev['safe_automation_pct'],
            'Absolute_Delta': final_dev['safe_automation_pct'] - 0.1511
        },
        {
            'Metric': 'Value Coverage %',
            'Original_P1': 0.1420,
            'Final_P7': final_dev['value_coverage_pct'],
            'Absolute_Delta': final_dev['value_coverage_pct'] - 0.1420
        },
        {
            'Metric': 'Precision',
            'Original_P1': 1.0,
            'Final_P7': final_dev['precision'],
            'Absolute_Delta': final_dev['precision'] - 1.0
        },
        {
            'Metric': 'False Auto-Match %',
            'Original_P1': 0.0,
            'Final_P7': final_dev['false_auto_match_pct'],
            'Absolute_Delta': final_dev['false_auto_match_pct'] - 0.0
        }
    ]
    with open(out_dir / "FINAL_DELTA_TABLE.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=['Metric', 'Original_P1', 'Final_P7', 'Absolute_Delta'])
        writer.writeheader()
        writer.writerows(delta_rows)

    # 4. Output FINAL_CONFIGURATION.json
    config_output = {
        'timestamp': datetime.now(UTC).isoformat(),
        'git': get_git_info(),
        'python_version': sys.version,
        'configuration': base_config,
        'allocator': 'OneToNAllocator (Stage E2)',
        'financial_control': 'FinancialControlEngine (Stage F)',
        'partitions': ['DEV', 'VALIDATION', 'TEST_ADVERSARIAL', 'FROZEN_UNSEEN'],
        'seeds': {
            'DEV': 'razorledger-dev-v1',
            'VALIDATION': 'razorledger-validation-v1',
            'TEST_ADVERSARIAL': 'razorledger-test_adversarial-v1',
            'FROZEN_UNSEEN': 'razorledger-frozen_unseen-v1'
        },
        'frozen': True
    }
    with open(out_dir / "FINAL_CONFIGURATION.json", "w") as f:
        json.dump(config_output, f, indent=2)

    print("Successfully generated all FINAL outputs in reports/final/")

if __name__ == "__main__":
    main()
