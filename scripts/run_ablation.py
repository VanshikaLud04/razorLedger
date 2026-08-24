import sys
import json
import pathlib

from app.matching.llm import GroqProvider, GeminiProvider
# Mock providers to fail fast without retries or quota usage during benchmarking
GroqProvider.generate = lambda self, p, s, max_attempts, run_id, batch_size: (False, "", 0, 0, 0.0, self.model)
GeminiProvider.generate = lambda self, p, s, max_attempts, run_id, batch_size: (False, "", 0, 0, 0.0, self.model)

from evaluation.ablation import AblationEvaluator

def main():
    print("Running A-F Ablation... this will take a moment.")
    evaluator = AblationEvaluator(seed='razorledger-dev-v1', partition='DEV')
    result = evaluator.run_ablation()
    
    report_dir = pathlib.Path('reports')
    report_dir.mkdir(exist_ok=True)
    
    with open('reports/baseline_ablation.txt', 'w') as f:
        f.write(result['report'])
        
    print(result['report'])
    
    json_data = {}
    for stage, res in result['results_by_stage'].items():
        json_data[stage] = {
            'metrics': res.metrics,
            'raw_metrics': res.raw_metrics
        }
        
    with open('reports/baseline_scorecard.json', 'w') as f:
        json.dump(json_data, f, indent=2)
        
    print("\nReports saved to reports/baseline_ablation.txt and reports/baseline_scorecard.json")

if __name__ == '__main__':
    main()
