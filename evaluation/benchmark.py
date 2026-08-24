from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class BenchmarkResult:
    metrics: dict = field(default_factory=dict)
    decisions: list = field(default_factory=list)
    raw_metrics: dict = field(default_factory=dict)

    @property
    def precision(self): return self.metrics.get('precision', 0.0)
    @property
    def recall(self): return self.metrics.get('recall', 0.0)
    @property
    def f1(self): return self.metrics.get('f1', 0.0)
    @property
    def safe_automation_rate(self): return self.metrics.get('safe_automation_rate', 0.0)
    @property
    def value_coverage_pct(self): return self.metrics.get('value_coverage_pct', 0.0)
    @property
    def false_auto_match_rate(self): return self.metrics.get('false_auto_match_rate', 0.0)
    @property
    def review_rate(self): return self.metrics.get('review_rate', 0.0)
    @property
    def pending_rate(self): return self.metrics.get('pending_rate', 0.0)
    @property
    def no_match_rate(self): return self.metrics.get('no_match_rate', 0.0)
    @property
    def non_automated_rate(self): return self.metrics.get('non_automated_rate', 0.0)
    @property
    def blocking_reduction_factor(self): return self.metrics.get('blocking_reduction_factor', 0.0)


class BenchmarkEvaluator:
    def __init__(self, truth_bundle, pipeline_result):
        self.truth_bundle = truth_bundle
        self.pipeline_result = pipeline_result
        self.decisions = pipeline_result.decisions

    def compute(self) -> BenchmarkResult:
        true_matches = 0
        false_auto_matches = 0
        total_value = 0
        verified_value = 0
        
        event_status = {}
        for sid, gid in self.truth_bundle.items():
            if gid:
                if gid not in event_status:
                    event_status[gid] = {'total_records': 0, 'correct_matches': 0}
                event_status[gid]['total_records'] += 1

        for dec in self.decisions:
            raw_sid = dec.source_event_id
            total_value += dec.amount_minor_units
            my_group = self.truth_bundle.get(raw_sid)

            if dec.action == 'MATCH':
                verified_value += dec.amount_minor_units
                chosen_sid = dec.chosen_candidate_sid
                if chosen_sid:
                    chosen_group = self.truth_bundle.get(chosen_sid)
                    if my_group and chosen_group and my_group == chosen_group:
                        true_matches += 1
                        event_status[my_group]['correct_matches'] += 1
                    else:
                        false_auto_matches += 1
                else:
                    false_auto_matches += 1

        auto_resolved = self.pipeline_result.auto_resolved
        false_auto_match_rate = false_auto_matches / auto_resolved if auto_resolved else 0.0
        value_coverage = verified_value / total_value if total_value else 0.0
        
        events_fully_resolved = sum(1 for status in event_status.values() 
                                  if status['total_records'] > 0 and 
                                  status['correct_matches'] == status['total_records'])

        llm_invoked = sum(1 for d in self.decisions if d.llm_provider)
        
        total = len(self.decisions)
        safe_automation_rate = auto_resolved / self.pipeline_result.accepted if self.pipeline_result.accepted else 0.0

        raw_metrics = {
            'total_events': len(event_status),
            'events_fully_resolved': events_fully_resolved,
            'total_source_records': self.pipeline_result.total_source_records,
            'deduplicated': self.pipeline_result.deduplicated,
            'accepted': self.pipeline_result.accepted,
            'total_decisions': total,
            'auto_resolved': auto_resolved,
            'review_count': self.pipeline_result.review_count,
            'no_match_count': self.pipeline_result.no_match_count,
            'pending_count': self.pipeline_result.pending_count,
            'naive_comparison_count': self.pipeline_result.naive_comparison_count,
            'candidate_pair_count': self.pipeline_result.candidate_pair_count,
            'true_matches': true_matches,
            'false_auto_matches': false_auto_matches,
            'total_value_minor': total_value,
            'verified_value_minor': verified_value,
            'llm_invoked': llm_invoked
        }
        
        metrics = {
            'precision': (true_matches / (true_matches + false_auto_matches)) if (true_matches + false_auto_matches) else 0.0,
            'recall': (true_matches / self.pipeline_result.accepted) if self.pipeline_result.accepted else 0.0,
            'f1': 0.0,
            'safe_automation_rate': safe_automation_rate,
            'review_rate': self.pipeline_result.review_rate,
            'no_match_rate': self.pipeline_result.no_match_rate,
            'pending_rate': self.pipeline_result.pending_rate,
            'non_automated_rate': self.pipeline_result.non_automated_rate,
            'value_coverage_pct': value_coverage,
            'false_auto_match_rate': false_auto_match_rate,
            'blocking_reduction_factor': self.pipeline_result.blocking_reduction_factor
        }
        
        p, r = metrics['precision'], metrics['recall']
        if p + r > 0:
            metrics['f1'] = 2 * (p * r) / (p + r)
            
        return BenchmarkResult(metrics=metrics, decisions=self.decisions, raw_metrics=raw_metrics)

    def generate_scorecard(self, label: str, result: BenchmarkResult, print_out=True):
        raw = result.raw_metrics
        met = result.metrics
        
        sep = '─' * 60
        out = []
        out.append(f"\n{'═'*60}")
        out.append(f"  RazorLedger — Run Scorecard: {label}")
        out.append(f"{'═'*60}")
        out.append(f"  Economic events total: {raw.get('total_events', 150):>6}")
        out.append(f"  Events fully resolved: {raw.get('events_fully_resolved', 0):>6}")
        out.append(sep)
        out.append(f"  Source records total : {raw.get('total_source_records', 0):>6}  (150 events × 3 sources)")
        out.append(f"  Deduplicated         : {raw.get('deduplicated', 0):>6}  (idempotency catches)")
        out.append(f"  Accepted into pipeline: {raw.get('accepted', 0):>5}")
        out.append(sep)
        out.append(f"  Decisions total      : {raw.get('total_decisions', 0):>6}")
        out.append(f"  MATCH (auto-resolved): {raw.get('auto_resolved', 0):>6}  ({met.get('safe_automation_rate', 0.0):>7.1%})")
        out.append(f"  REVIEW               : {raw.get('review_count', 0):>6}  ({met.get('review_rate', 0.0):>7.1%})")
        out.append(f"  NO_MATCH             : {raw.get('no_match_count', 0):>6}  ({met.get('no_match_rate', 0.0):>7.1%})")
        out.append(f"  PENDING              : {raw.get('pending_count', 0):>6}  ({met.get('pending_rate', 0.0):>7.1%})")
        
        non_automated = raw.get('review_count', 0) + raw.get('no_match_count', 0) + raw.get('pending_count', 0)
        out.append(f"  Non-automated total  : {non_automated:>6}  ({met.get('non_automated_rate', 0.0):>7.1%})")
        out.append(sep)
        out.append(f"  Blocking: naive={raw.get('naive_comparison_count', 0):,}  "
                   f"candidates={raw.get('candidate_pair_count', 0):,}  "
                   f"reduction={met.get('blocking_reduction_factor', 0.0):.1f}x")
        out.append(sep)
        out.append("  HERO METRICS (in priority order):")
        out.append(f"  1. Safe automation rate    : {met.get('safe_automation_rate', 0.0):>7.1%}")
        
        val_ver = raw.get('verified_value_minor', 0) // 100
        val_tot = raw.get('total_value_minor', 0) // 100
        out.append(f"  2. Value coverage          : {met.get('value_coverage_pct', 0.0):>7.1%}  "
                   f"(₹{val_ver:,} of ₹{val_tot:,})")
        out.append(f"  3. False auto-match rate   : {met.get('false_auto_match_rate', 0.0):>7.1%}  "
                   f"({raw.get('false_auto_matches', 0)} wrong auto-matches)")
        out.append(f"  4. Review rate             : {met.get('review_rate', 0.0):>7.1%}")
        out.append(f"  5. Adversarial holdout     : {'N/A (P1)':>12}")
        out.append(sep)
        out.append(f"  True matches (verified)  : {raw.get('true_matches', 0):>6}")
        out.append(f"  False auto-matches       : {raw.get('false_auto_matches', 0):>6}")
        out.append(f"{'═'*60}\n")
        
        text_out = "\n".join(out)
        if print_out:
            print(text_out)
        
        return text_out
