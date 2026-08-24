import sys
import copy
from typing import List, Dict, Any

from app.pipeline import ReconciliationPipeline
from evaluation.benchmark import BenchmarkEvaluator, BenchmarkResult
from generator.config import GeneratorConfig
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver
from app.matching.evidence import compute_rarity_frequencies

class AblationEvaluator:
    def __init__(self, seed: str = 'test_ablation', partition: str = 'DEV'):
        self.seed = seed
        self.partition = partition
        
        # Identical dataset generation for all stages
        cfg = GeneratorConfig(seed=self.seed, partition=self.partition)
        events = EconomicEventGenerator(cfg).generate()
        raw_records, truth_list = SourceViewDeriver(cfg).derive(events)
        
        self.truth_bundle = {}
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
            self.truth_bundle[sid] = truth_group
            clean_records.append(r)
            
        self.rarity = compute_rarity_frequencies(clean_records)
        self.clean_records = clean_records
        
    def run_ablation(self) -> dict:
        stages = {
            'A': {'B_FUZZY', 'C_SEMANTIC', 'D_SCORER', 'E_LLM', 'F_VERIFIER'},
            'B': {'C_SEMANTIC', 'D_SCORER', 'E_LLM', 'F_VERIFIER'},
            'C': {'D_SCORER', 'E_LLM', 'F_VERIFIER'},
            'D': {'E_LLM', 'F_VERIFIER'},
            'E': {'F_VERIFIER'},
            'F': set()
        }
        
        results = {}
        ordered_stages = ['A', 'B', 'C', 'D', 'E', 'F']
        
        for stage in ordered_stages:
            disabled = stages[stage]
            # Initialize identical pipeline parameters, only changing disabled_stages
            pipe = ReconciliationPipeline(rarity_frequencies=self.rarity, disabled_stages=disabled)
            res = pipe.run(copy.deepcopy(self.clean_records), seed=self.seed)
            evaluator = BenchmarkEvaluator(self.truth_bundle, res)
            results[stage] = evaluator.compute()
            
        return self._format_ablation(ordered_stages, results)
        
    def _format_ablation(self, ordered_stages: list, results: Dict[str, BenchmarkResult]) -> dict:
        table = []
        headers = ["Stage", "Precision", "Recall", "F1", "Safe Automation", "Value Coverage", "False Auto-Match", "Review", "Pending"]
        
        def row_str(name, metrics):
            return (f"{name:<5} | "
                    f"{metrics.get('precision', 0.0):>8.1%} | "
                    f"{metrics.get('recall', 0.0):>5.1%} | "
                    f"{metrics.get('f1', 0.0):>4.1%} | "
                    f"{metrics.get('safe_automation_rate', 0.0):>14.1%} | "
                    f"{metrics.get('value_coverage_pct', 0.0):>13.1%} | "
                    f"{metrics.get('false_auto_match_rate', 0.0):>15.1%} | "
                    f"{metrics.get('review_rate', 0.0):>5.1%} | "
                    f"{metrics.get('pending_rate', 0.0):>6.1%}")

        table.append(" | ".join(headers))
        table.append("-" * 110)
        
        for stage in ordered_stages:
            table.append(row_str(stage, results[stage].metrics))
            
        table.append("")
        table.append("Incremental Deltas:")
        table.append("-" * 110)
        
        for i in range(1, len(ordered_stages)):
            prev = ordered_stages[i-1]
            curr = ordered_stages[i]
            prev_met = results[prev].metrics
            curr_met = results[curr].metrics
            
            delta_met = {k: curr_met.get(k, 0.0) - prev_met.get(k, 0.0) for k in curr_met}
            # Adding sign indicator for deltas
            def signed_pct(val):
                if val > 0: return f"+{val:.1%}"
                if val == 0: return f" {val:.1%}"
                return f"{val:.1%}"
                
            row = (f"{curr}-{prev:<3} | "
                   f"{signed_pct(delta_met.get('precision', 0.0)):>8} | "
                   f"{signed_pct(delta_met.get('recall', 0.0)):>5} | "
                   f"{signed_pct(delta_met.get('f1', 0.0)):>4} | "
                   f"{signed_pct(delta_met.get('safe_automation_rate', 0.0)):>14} | "
                   f"{signed_pct(delta_met.get('value_coverage_pct', 0.0)):>13} | "
                   f"{signed_pct(delta_met.get('false_auto_match_rate', 0.0)):>15} | "
                   f"{signed_pct(delta_met.get('review_rate', 0.0)):>5} | "
                   f"{signed_pct(delta_met.get('pending_rate', 0.0)):>6}")
            table.append(row)
            
        return {
            'status': 'SUCCESS',
            'results_by_stage': results,
            'report': "\n".join(table)
        }
