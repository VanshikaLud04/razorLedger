import sys
import copy
import json
import csv
import pathlib
import collections
import statistics

# Attempt to load matplotlib for PNGs
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from app.pipeline import ReconciliationPipeline, load_config
from generator.config import GeneratorConfig
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver
from app.matching.evidence import compute_rarity_frequencies

from app.matching.llm import GroqProvider, GeminiProvider
GroqProvider.generate = lambda self, p, s, max_attempts, run_id, batch_size: (False, "", 0, 0, 0.0, self.model)
GeminiProvider.generate = lambda self, p, s, max_attempts, run_id, batch_size: (False, "", 0, 0, 0.0, self.model)

def main():
    report_dir = pathlib.Path('reports')
    report_dir.mkdir(exist_ok=True)
    
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
    
    base_config = load_config()
    
    print("Running Full Pipeline (F)...")
    pipe_f = ReconciliationPipeline(config=copy.deepcopy(base_config), rarity_frequencies=rarity)
    res_f = pipe_f.run(copy.deepcopy(clean_records), seed=seed)
    
    print("Running Pipeline without F (E)...")
    pipe_e = ReconciliationPipeline(config=copy.deepcopy(base_config), rarity_frequencies=rarity, disabled_stages={'F_VERIFIER'})
    res_e = pipe_e.run(copy.deepcopy(clean_records), seed=seed)
    
    print("Running Pipeline without D, E, F (C)...")
    pipe_c = ReconciliationPipeline(config=copy.deepcopy(base_config), rarity_frequencies=rarity, disabled_stages={'D_SCORER', 'E_LLM', 'F_VERIFIER'})
    res_c = pipe_c.run(copy.deepcopy(clean_records), seed=seed)
    
    print("Running Pipeline without E, F (D)...")
    pipe_d = ReconciliationPipeline(config=copy.deepcopy(base_config), rarity_frequencies=rarity, disabled_stages={'E_LLM', 'F_VERIFIER'})
    res_d = pipe_d.run(copy.deepcopy(clean_records), seed=seed)
    
    total_records = len(clean_records)
    total_value = sum(r['amount_minor_units'] for r in clean_records)
    
    decisions_f = {d.source_event_id: d for d in res_f.decisions}
    auto_matched_recs = [d for d in res_f.decisions if d.action == 'MATCH']
    safely_auto_matched_recs = [d for d in auto_matched_recs if truth_bundle.get(d.source_event_id) == truth_bundle.get(d.chosen_candidate_sid)]
    
    safely_auto_value = sum(d.amount_minor_units for d in safely_auto_matched_recs)
    
    value_coverage_analysis = {
        'total_records': total_records,
        'auto_matched_records': len(auto_matched_recs),
        'record_automation_rate': len(auto_matched_recs) / total_records if total_records else 0,
        'total_transaction_value': total_value,
        'safely_auto_matched_value': safely_auto_value,
        'value_coverage_pct': safely_auto_value / total_value if total_value else 0,
    }
    
    with open(report_dir / 'value_coverage_analysis.json', 'w') as f:
        json.dump(value_coverage_analysis, f, indent=2)
        
    decisions_e = {d.source_event_id: d for d in res_e.decisions}
    f_rejected = []
    control_violation_counts = collections.Counter()
    control_violation_values = collections.Counter()
    
    for sid, d_e in decisions_e.items():
        if d_e.action == 'MATCH':
            d_f = decisions_f.get(sid)
            if d_f and d_f.action != 'MATCH':
                f_rejected.append({
                    'sid': sid,
                    'value': d_f.amount_minor_units,
                    'reason': d_f.primary_reason,
                    'control_result': d_f.control_result,
                    'was_correct': truth_bundle.get(sid) == truth_bundle.get(d_e.chosen_candidate_sid)
                })
                control_violation_counts[d_f.control_result] += 1
                control_violation_values[d_f.control_result] += d_f.amount_minor_units
                
    with open(report_dir / 'control_rejection_analysis.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['control_result', 'count', 'total_value', 'genuinely_unsafe_count', 'false_positive_count'])
        for ctrl, count in control_violation_counts.items():
            unsafe = sum(1 for r in f_rejected if r['control_result'] == ctrl and not r['was_correct'])
            fp = sum(1 for r in f_rejected if r['control_result'] == ctrl and r['was_correct'])
            writer.writerow([ctrl, count, control_violation_values[ctrl], unsafe, fp])
            
    decisions_c = {d.source_event_id: d for d in res_c.decisions}
    decisions_d = {d.source_event_id: d for d in res_d.decisions}
    
    d_promoted = []
    for sid, d_c in decisions_c.items():
        if d_c.action != 'MATCH':
            d_d = decisions_d.get(sid)
            if d_d and d_d.action == 'MATCH':
                d_promoted.append({
                    'sid': sid,
                    'c_confidence': d_c.confidence,
                    'd_confidence': d_d.confidence,
                    'was_correct': truth_bundle.get(sid) == truth_bundle.get(d_d.chosen_candidate_sid)
                })
    print(f"C -> D promoted {len(d_promoted)} records. Correct: {sum(1 for r in d_promoted if r['was_correct'])}")

    opportunities = collections.defaultdict(lambda: {'count': 0, 'value': 0, 'correct_candidate_available': 0})
    for d in res_f.decisions:
        if d.action in ('MATCH', 'PENDING'):
            continue
            
        reason = d.primary_reason
        has_correct = False
        target_group = truth_bundle.get(d.source_event_id)
        if target_group:
            for sid, grp in truth_bundle.items():
                if sid != d.source_event_id and grp == target_group:
                    has_correct = True
                    break
                    
        cat = 'Unknown'
        if d.control_result and 'FAIL' in d.control_result:
            cat = 'Control Failure'
        elif reason and 'BELOW_THRESHOLD' in reason:
            cat = 'Confidence Below Auto-Match Threshold'
        elif reason and 'CONFIDENCE_GAP_INSUFFICIENT' in reason:
            cat = 'Ambiguous / Low Gap'
        elif reason == 'NO_CANDIDATE':
            cat = 'No Candidate (Blocked or Missing)'
        elif reason and 'INSUFFICIENT_EVIDENCE' in reason:
            cat = 'Insufficient Evidence Families'
            
        opportunities[cat]['count'] += 1
        opportunities[cat]['value'] += d.amount_minor_units
        if has_correct:
            opportunities[cat]['correct_candidate_available'] += 1

    with open(report_dir / 'opportunity_ranked.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Opportunity', 'Records', 'Value', 'Correct Candidate in DB'])
        for cat, data in sorted(opportunities.items(), key=lambda x: x[1]['value'], reverse=True):
            writer.writerow([cat, data['count'], data['value'], data['correct_candidate_available']])
            
    if HAS_MATPLOTLIB:
        plt.figure()
        plt.bar(['Total', 'Safely Matched'], [total_value, safely_auto_value])
        plt.title('Value Coverage')
        plt.savefig(report_dir / 'value_coverage.png')
        
        plt.figure()
        labels = list(opportunities.keys())
        vals = [d['value'] for d in opportunities.values()]
        if vals and sum(vals) > 0:
            plt.pie(vals, labels=labels, autopct='%1.1f%%')
            plt.title('Review Burden by Value')
            plt.savefig(report_dir / 'review_burden.png')

    print("Phase 3 Analysis Complete. Outputs written to reports/ directory.")

if __name__ == '__main__':
    main()
