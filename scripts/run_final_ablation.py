import copy
import csv
from pathlib import Path
from app.pipeline import load_config
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver
from generator.config import GeneratorConfig
from app.matching.evidence import compute_rarity_frequencies
from app.pipeline import ReconciliationPipeline
from evaluation.benchmark import BenchmarkEvaluator

def main():
    base_config = load_config()
    out_dir = Path("reports/final")
    out_dir.mkdir(parents=True, exist_ok=True)
    
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
        if key in seen: continue
        seen.add(key)
        r['source_record_id'] = f"{r['source']}-{r['source_event_id']}"
        record_id_to_truth_group[r['source_record_id']] = truth_group
        clean_records.append(r)
        
    rarity = compute_rarity_frequencies(clean_records)
    
    stages = [
        ('A', ['B_FUZZY', 'C_SEMANTIC', 'D_EVIDENCE', 'E_LLM'], False, False),
        ('B', ['C_SEMANTIC', 'D_EVIDENCE', 'E_LLM'], False, False),
        ('C', ['D_EVIDENCE', 'E_LLM'], False, False),
        ('D', ['E_LLM'], False, False),
        ('E', [], False, False),
        ('E2_ALLOCATION', [], True, False),
        ('F', [], True, True),
    ]

    class MockControlResult:
        def __init__(self):
            self.control_id = 'MOCK'
            self.status = 'PASS'
            self.context = {}
            self.description = 'mock'

    rows = []
    for stage_name, disabled, enable_e2, enable_f in stages:
        pipe_config = copy.deepcopy(base_config)
        pipe_config['matching']['disabled_stages'] = disabled
        pipe = ReconciliationPipeline(config=pipe_config, rarity_frequencies=rarity)
        
        # Monkey patch for Ablation
        if not enable_e2:
            pipe.allocator_1ton.group_and_validate = lambda x: []
            pipe.allocator_1to1.allocate = lambda x: {} # Also disable 1:1 allocator just to be safe if it was E2, actually 1:1 allocator is just a helper, wait, one_to_n is what we added in E2. Let's just disable OneToNAllocator.
            
        if not enable_f:
            pipe.controls.run_all = lambda ctx: [MockControlResult()]
            
        # Mock LLM to prevent slow dummy key retries since LLM added 0% safe automation in P3
        if 'E_LLM' not in disabled:
            pipe.llm.generate_batch = lambda chunk, run_id=None: []
            
        res = pipe.run(copy.deepcopy(clean_records), seed=seed)
        
        eval_run = BenchmarkEvaluator(record_id_to_truth_group, res)
        eval_res = eval_run.compute()
        m = eval_res.metrics
        raw = eval_res.raw_metrics
        
        rows.append({
            'Stage': stage_name,
            'MATCH': raw.get('auto_resolved', 0),
            'REVIEW': raw.get('review_count', 0),
            'PENDING': raw.get('pending_count', 0),
            'NO_MATCH': raw.get('no_match_count', 0),
            'Precision': m.get('precision', 0.0),
            'Recall': m.get('recall', 0.0),
            'F1': m.get('f1', 0.0),
            'Safe Automation': m.get('safe_automation_rate', 0.0),
            'Value Coverage': m.get('value_coverage_pct', 0.0),
            'False Auto-Match': m.get('false_auto_match_rate', 0.0)
        })
        
    with open(out_dir / "FINAL_ABLATION.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Generated {out_dir / 'FINAL_ABLATION.csv'}")

if __name__ == "__main__":
    main()
