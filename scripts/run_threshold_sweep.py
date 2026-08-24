import sys
import csv
import pathlib
import copy

from app.pipeline import ReconciliationPipeline, load_config
from evaluation.benchmark import BenchmarkEvaluator
from generator.config import GeneratorConfig
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver
from app.matching.evidence import compute_rarity_frequencies

# Mock providers to fail fast without retries or quota usage during benchmarking
from app.matching.llm import GroqProvider, GeminiProvider
GroqProvider.generate = lambda self, p, s, max_attempts, run_id, batch_size: (False, "", 0, 0, 0.0, self.model)
GeminiProvider.generate = lambda self, p, s, max_attempts, run_id, batch_size: (False, "", 0, 0, 0.0, self.model)

def main():
    print("Running Threshold Sweep on DEV partition...")
    seed = 'razorledger-dev-v1'
    partition = 'DEV'
    
    cfg = GeneratorConfig(seed=seed, partition=partition)
    events = EconomicEventGenerator(cfg).generate()
    raw_records, truth_list = SourceViewDeriver(cfg).derive(events)
    
    truth_bundle = {}
    clean_records = []
    seen = set()
    for rec in raw_records:
        r = copy.copy(rec)
        truth_group = r.pop('ground_truth_group_id', None)
        key = (r['source'], r['source_event_id'])
        if key in seen:
            continue
        seen.add(key)
        sid = f"{r['source']}-{r['source_event_id']}"
        r['source_record_id'] = sid
        truth_bundle[sid] = truth_group
        clean_records.append(r)
        
    rarity = compute_rarity_frequencies(clean_records)
    
    thresholds = [0.80, 0.82, 0.84, 0.85, 0.86, 0.88, 0.90, 0.92, 0.94, 0.96, 0.98]
    
    report_dir = pathlib.Path('reports')
    report_dir.mkdir(exist_ok=True)
    
    csv_path = report_dir / 'threshold_sweep.csv'
    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = [
            'threshold', 'precision', 'recall', 'f1', 'safe_automation_rate', 
            'value_coverage_pct', 'false_auto_matches', 'false_auto_match_rate',
            'review_rate', 'pending_rate'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        base_config = load_config()
        if 'matching' not in base_config:
            base_config['matching'] = {}
            
        for t in thresholds:
            print(f"Testing threshold: {t:.2f}")
            run_config = copy.deepcopy(base_config)
            run_config['matching']['auto_match_threshold'] = t
            
            pipe = ReconciliationPipeline(config=run_config, rarity_frequencies=rarity)
            
            res = pipe.run(copy.deepcopy(clean_records), seed=seed)
            evaluator = BenchmarkEvaluator(truth_bundle, res)
            eval_result = evaluator.compute()
            metrics = eval_result.metrics
            raw_metrics = eval_result.raw_metrics
            
            writer.writerow({
                'threshold': f"{t:.2f}",
                'precision': f"{metrics.get('precision', 0):.4f}",
                'recall': f"{metrics.get('recall', 0):.4f}",
                'f1': f"{metrics.get('f1', 0):.4f}",
                'safe_automation_rate': f"{metrics.get('safe_automation_rate', 0):.4f}",
                'value_coverage_pct': f"{metrics.get('value_coverage_pct', 0):.4f}",
                'false_auto_matches': raw_metrics.get('false_auto_matches', 0),
                'false_auto_match_rate': f"{metrics.get('false_auto_match_rate', 0):.4f}",
                'review_rate': f"{metrics.get('review_rate', 0):.4f}",
                'pending_rate': f"{metrics.get('pending_rate', 0):.4f}"
            })
            
    print(f"\nSweep complete. Results written to {csv_path}")

if __name__ == '__main__':
    main()
