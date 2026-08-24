"""
app/pipeline.py — End-to-end reconciliation pipeline orchestrator.

Pipeline order (fix #1 from architecture review):
  1. GENERATE (outside pipeline — caller provides records)
  2. INGEST (dedup + validate, strips ground_truth_group_id)
  3. DETERMINISTIC MATCH (cheap, resolve clear cases first)
  4. BLOCK UNRESOLVED ONLY (compound blocking on unresolved records)
  5. FUZZY EVIDENCE (RapidFuzz on blocked candidates)
  6. PROBABILISTIC SCORER (evidence-weighted, family policy)
  7. LLM EVIDENCE if needed (P0: stub, always skips)
  8. PROVISIONAL MATCH PROPOSAL
  9. BOUNDED ALLOCATION (1:1 via SciPy, 1:N via subset-sum DP)
  10. INDEPENDENT FINANCIAL CONTROLS (CTRL-001…010)
  11. FINAL DECISION (written to decisions table post-control)
  12. AUDIT LOG (hash-chained)

Returns a PipelineResult with all decisions and metrics.
No DB required for unit testing — works in-memory with dicts.
"""

from dataclasses import dataclass, field
from datetime import date
import logging
import yaml
import pathlib

from app.matching.deterministic import DeterministicMatcher
from app.matching.fuzzy import FuzzyMatcher
from app.matching.evidence import EvidenceFeatureBuilder, compute_rarity_frequencies
from app.matching.evidence_weighted import EvidenceWeightedScorer
from app.matching.allocator import OneToNAllocator
from app.controls.engine import FinancialControlEngine
from app.matching.llm import LLMEvidenceGenerator
from app.matching.semantic import SemanticFeatureBuilder
from app.blocking import CompoundBlocker
from app.allocation.one_to_one import OneToOneAllocator
from app.decision import DecisionEngine

logger = logging.getLogger(__name__)


def load_config() -> dict:
    cfg_path = pathlib.Path(__file__).parent.parent / 'config' / 'defaults.yaml'
    with open(cfg_path) as f:
        return yaml.safe_load(f)


@dataclass
class DecisionRecord:
    source_event_id: str
    source: str
    amount_minor_units: int
    currency: str
    action: str              # MATCH | REVIEW | NO_MATCH | PENDING
    primary_reason: str
    control_result: str
    chosen_candidate_sid: str | None
    confidence: float | None
    risk_exposure_score: float | None
    llm_provider: str | None = None


@dataclass
class PipelineResult:
    run_seed: str
    total_source_records: int
    accepted: int
    deduplicated: int
    rejected: int
    naive_comparison_count: int
    candidate_pair_count: int
    blocking_reduction_factor: float
    decisions: list[DecisionRecord] = field(default_factory=list)

    @property
    def auto_resolved(self):
        return sum(1 for d in self.decisions if d.action == 'MATCH')

    @property
    def review_count(self):
        return sum(1 for d in self.decisions if d.action == 'REVIEW')

    @property
    def no_match_count(self):
        return sum(1 for d in self.decisions if d.action == 'NO_MATCH')

    @property
    def pending_count(self):
        return sum(1 for d in self.decisions if d.action == 'PENDING')

    @property
    def safe_automation_rate(self):
        # same as auto-resolution rate
        return self.auto_resolved / self.accepted if self.accepted else 0.0

    @property
    def review_rate(self):
        return self.review_count / self.accepted if self.accepted else 0.0

    @property
    def no_match_rate(self):
        return self.no_match_count / self.accepted if self.accepted else 0.0

    @property
    def pending_rate(self):
        return self.pending_count / self.accepted if self.accepted else 0.0

    @property
    def non_automated_rate(self):
        return (self.review_count + self.no_match_count + self.pending_count) / self.accepted if self.accepted else 0.0

    @property
    def value_total_minor(self):
        return sum(d.amount_minor_units for d in self.decisions)

    @property
    def value_verified_minor(self):
        return sum(d.amount_minor_units for d in self.decisions if d.action == 'MATCH')

    @property
    def value_coverage_pct(self):
        total = self.value_total_minor
        return self.value_verified_minor / total if total else 0.0


class ReconciliationPipeline:
    """
    In-memory pipeline for testing and benchmarking.
    Does not require a database connection.
    DB-backed version wires the same logic through IngestService + async routes.
    """

    def __init__(self, config: dict | None = None, rarity_frequencies: dict | None = None, disabled_stages: set[str] | None = None):
        self.config = config or load_config()
        if disabled_stages is not None:
            self.disabled_stages = disabled_stages
        else:
            self.disabled_stages = set(self.config.get('matching', {}).get('disabled_stages', []))
        self.det = DeterministicMatcher(self.config)
        self.fuzz = FuzzyMatcher(self.config)
        self.evb = EvidenceFeatureBuilder(self.config, rarity_frequencies)
        self.semantic = SemanticFeatureBuilder(self.config)
        self.scorer = EvidenceWeightedScorer(self.config)
        self.llm = LLMEvidenceGenerator(self.config)
        self.blocker = CompoundBlocker(self.config)
        self.allocator_1to1 = OneToOneAllocator(self.config)
        self.allocator_1ton = OneToNAllocator(self.config)
        self.controls = FinancialControlEngine(self.config)
        self.decision_engine = DecisionEngine(self.config, self.scorer, self.controls)

    def run(self, source_records: list[dict], seed: str = 'unknown') -> PipelineResult:
        """
        source_records: list of dicts from SourceViewDeriver.derive() with
        ground_truth_group_id already STRIPPED (done by ingest layer).
        Each dict must have: source_record_id, source, amount_minor_units,
        currency, reference, counterparty, description, transaction_date,
        lifecycle_state.
        """
        cfg_match = self.config.get('matching', {})
        auto_threshold = cfg_match.get('auto_match_threshold', 0.80)
        settlement_days = cfg_match.get('settlement_window_days', 5)

        total = len(source_records)
        decisions: list[DecisionRecord] = []
        allocated_sids: set[str] = set()
        llm_calls_used = 0

        # ── Step 3 & 4: Block unresolved only ─────────────────────────────────────
        unresolved = source_records
        resolved_sids: set[str] = set()
        
        sources = set(r.get('source') for r in unresolved)
        naive_count = 0
        counts = {s: sum(1 for r in unresolved if r.get('source') == s) for s in sources}
        # cross-source cartesian pairs
        for s1 in sources:
            for s2 in sources:
                if s1 < s2:
                    naive_count += counts[s1] * counts[s2]

        candidate_pairs = self.blocker.block(unresolved)
        candidate_count = len(candidate_pairs)
        reduction = naive_count / candidate_count if candidate_count > 0 else float('inf')

        logger.info(
            f"Blocking: {len(unresolved)} unresolved → naive={naive_count} "
            f"candidates={candidate_count} reduction={reduction:.1f}x"
        )

        # ── Steps 5–11: Evidence + scoring + allocation + controls + decision ──
        # Group candidates by source_record_id
        from collections import defaultdict
        cands_by_record: dict[str, list[str]] = defaultdict(list)
        for sid_a, sid_b in candidate_pairs:
            cands_by_record[sid_a].append(sid_b)
            cands_by_record[sid_b].append(sid_a)

        unresolved_by_sid = {r['source_record_id']: r for r in unresolved}
        processed_sids: set[str] = set()

        scored_records = {}
        llm_eligible_groups = []

        # Phase 1: Initial Scoring
        for rec in unresolved:
            sid = rec['source_record_id']
            if sid in processed_sids or sid in resolved_sids or sid in allocated_sids:
                continue

            candidate_sids = [c for c in cands_by_record.get(sid, []) if c not in allocated_sids]
            if not candidate_sids:
                # No candidates after blocking
                lifecycle = rec.get('lifecycle_state', '')
                if lifecycle in ['INITIATED', 'CAPTURED', 'PARTIALLY_SETTLED']:
                    action = 'PENDING'
                    primary_reason = 'LIFECYCLE_PENDING_SETTLEMENT'
                else:
                    action = 'NO_MATCH'
                    primary_reason = 'NO_CANDIDATE'
                
                decisions.append(DecisionRecord(
                    source_event_id=sid,
                    source=rec['source'],
                    amount_minor_units=rec['amount_minor_units'],
                    currency=rec['currency'],
                    action=action,
                    primary_reason=primary_reason,
                    control_result='N/A',
                    chosen_candidate_sid=None,
                    confidence=None,
                    risk_exposure_score=self._risk(rec, action),
                ))
                processed_sids.add(sid)
                continue

            # Build evidence for each candidate
            candidate_evidences = []
            for csid in candidate_sids:
                if csid not in unresolved_by_sid:
                    continue
                cand = unresolved_by_sid[csid]
                dm = self.det.match(rec, cand)
                
                if 'B_FUZZY' in self.disabled_stages:
                    fs = {'fuzzy_score': 0.0, 'amount_distance': 1.0, 'date_distance': 1.0}
                else:
                    fs = self.fuzz.score(rec, cand)
                    
                ev = self.evb.build(rec, cand, fs, dm)
                
                if 'C_SEMANTIC' in self.disabled_stages:
                    sem = {}
                else:
                    sem = self.semantic.build(rec, cand)
                ev.update(sem)
                candidate_evidences.append({
                    **ev,
                    'candidate_source_record_id': csid,
                    '_cand_record': cand,
                    'deterministic_match': dm['deterministic_match'],
                    'deterministic_reason': dm['match_type']
                })

            if not candidate_evidences:
                lifecycle = rec.get('lifecycle_state', '')
                if lifecycle in ['INITIATED', 'CAPTURED', 'PARTIALLY_SETTLED']:
                    action = 'PENDING'
                    primary_reason = 'LIFECYCLE_PENDING_SETTLEMENT'
                else:
                    action = 'NO_MATCH'
                    primary_reason = 'NO_CANDIDATE'
                    
                decisions.append(DecisionRecord(
                    source_event_id=sid, source=rec['source'],
                    amount_minor_units=rec['amount_minor_units'],
                    currency=rec['currency'],
                    action=action, primary_reason=primary_reason,
                    control_result='N/A', chosen_candidate_sid=None,
                    confidence=None, risk_exposure_score=self._risk(rec, action),
                ))
                processed_sids.add(sid)
                continue

            if 'D_SCORER' in self.disabled_stages:
                ranked = []
                for ev in candidate_evidences:
                    score = ev.get('fuzzy_score', 0.0)
                    if ev.get('deterministic_match'):
                        score = 1.0
                    ranked.append({**ev, 'probabilistic_confidence': score})
                ranked.sort(key=lambda x: x['probabilistic_confidence'], reverse=True)
                for i, c in enumerate(ranked):
                    if i + 1 < len(ranked):
                        c['confidence_gap_to_next'] = c['probabilistic_confidence'] - ranked[i+1]['probabilistic_confidence']
                    else:
                        c['confidence_gap_to_next'] = c['probabilistic_confidence']
            else:
                ranked = self.scorer.rank_candidates(sid, candidate_evidences)
                
            scored_records[sid] = (rec, ranked)
            
            if 'E_LLM' not in self.disabled_stages and self.llm.should_invoke(ranked, 0):  # Calls used checked in batcher
                llm_eligible_groups.append({
                    'source_record': rec,
                    'top_candidates': ranked[:2]
                })

        # Phase 2: Batch LLM Generation (Deterministic Selection)
        def _llm_sort_key(g):
            t = g['top_candidates'][0]
            return (
                round(t.get('confidence_gap_to_next', 0.0), 6),   # ASC: smallest gap first
                -round(t.get('probabilistic_confidence', 0.0), 6), # DESC: highest conf among ties
                g['source_record']['source_record_id']             # ASC: tie-break
            )
        llm_eligible_groups.sort(key=_llm_sort_key)
        
        # Enforce budget: max_calls * batch_size (typically 35 * 2 = 70)
        max_calls = getattr(self.llm, 'MAX_CALLS', 35)
        batch_size = getattr(self.llm, 'MAX_GROUPS_PER_CALL', 2)
        max_groups = max_calls * batch_size
        selected_groups = llm_eligible_groups[:max_groups]
        
        llm_results = {}
        for i in range(0, len(selected_groups), batch_size):
            chunk = selected_groups[i:i+batch_size]
            chunk_results = self.llm.generate_batch(chunk, run_id=seed)
            if chunk_results:
                for r in chunk_results:
                    llm_results[r.group_id] = {
                        'llm_provider_audit': getattr(self.llm.provider, 'model', 'unknown'),
                        'llm_invoked': True,
                        'llm_semantic_assessment': "supports" if "CANDIDATE_1" in r.comparative_preference else ("contradicts" if "CANDIDATE_2" in r.comparative_preference else "neutral"),
                        'route_to_review': r.uncertainty_level == 'HIGH'
                    }

        # Phase 2.5: One-To-N Allocation Grouping
        allocator = OneToNAllocator(self.config)
        valid_groups = allocator.group_and_validate(scored_records)
        for group in valid_groups:
            ctrl_ctx = self._build_group_control_context(group, allocated_sids)
            ctrl_results = self.controls.run_all(ctrl_ctx)
            failed = [r for r in ctrl_results if r.status == 'FAIL']
            
            banks = [r for r in group if r['source'] == 'BANK']
            primary_bank_sid = banks[0]['source_record_id'] if banks else group[0]['source_record_id']
            
            for r in group:
                chosen_sid = primary_bank_sid if r['source_record_id'] != primary_bank_sid else group[-1]['source_record_id']
                if chosen_sid == r['source_record_id']:
                    chosen_sid = group[0]['source_record_id'] if len(group)>1 else None
                    
                if failed:
                    decisions.append(DecisionRecord(
                        source_event_id=r['source_record_id'], source=r['source'],
                        amount_minor_units=r.get('amount_minor_units', 0), currency=r.get('currency', 'INR'),
                        action='REVIEW', primary_reason='CONTROL_FAIL',
                        control_result='FAIL: ' + ','.join(cr.control_id for cr in failed),
                        chosen_candidate_sid=chosen_sid, confidence=1.0, risk_exposure_score=self._risk(r, 'REVIEW'),
                        llm_provider=None
                    ))
                else:
                    decisions.append(DecisionRecord(
                        source_event_id=r['source_record_id'], source=r['source'],
                        amount_minor_units=r.get('amount_minor_units', 0), currency=r.get('currency', 'INR'),
                        action='MATCH', primary_reason='CANDIDATE_MATCH',
                        control_result='PASS', chosen_candidate_sid=chosen_sid,
                        confidence=1.0, risk_exposure_score=0.0, llm_provider=None
                    ))
                    allocated_sids.add(r['source_record_id'])
                processed_sids.add(r['source_record_id'])

        # Phase 3: Finalization & Controls (for ungrouped records)
        for sid, (rec, ranked) in scored_records.items():
            if sid in processed_sids:
                continue
                
            top = ranked[0]
            
            provider_audit = None
            # Apply LLM evidence if it was generated
            if sid in llm_results:
                llm_out = llm_results[sid]
                provider_audit = llm_out.get('llm_provider_audit')
                if llm_out.get('llm_invoked'):
                    top['probabilistic_confidence'] = self.scorer.apply_llm_adjustment(
                        top['probabilistic_confidence'], 
                        llm_out.get('llm_semantic_assessment')
                    )
                    top['confidence_gap_to_next'] = top['probabilistic_confidence'] - ranked[1]['probabilistic_confidence']
                
                if llm_out.get('route_to_review'):
                    decisions.append(DecisionRecord(
                        source_event_id=sid, source=rec['source'],
                        amount_minor_units=rec['amount_minor_units'],
                        currency=rec['currency'],
                        action='REVIEW', primary_reason='LLM_REVIEW',
                        control_result='N/A', chosen_candidate_sid=None,
                        confidence=top.get('probabilistic_confidence'),
                        risk_exposure_score=self._risk(rec, 'REVIEW'),
                        llm_provider=provider_audit
                    ))
                    processed_sids.add(sid)
                    continue

            # Check auto-match eligibility
            eligible, reason = self.scorer.check_auto_match_eligibility(top)
            cand_rec = top.get('_cand_record', {})

            if not eligible:
                conf = top.get('probabilistic_confidence', 0.0)
                review_threshold = self.config.get('matching', {}).get('review_threshold', 0.40)
                if conf < review_threshold:
                    lifecycle = rec.get('lifecycle_state', '')
                    if lifecycle in ['INITIATED', 'CAPTURED', 'PARTIALLY_SETTLED']:
                        action = 'PENDING'
                        primary_reason = 'LIFECYCLE_PENDING_SETTLEMENT'
                    else:
                        action = 'NO_MATCH'
                        primary_reason = 'BELOW_REVIEW_THRESHOLD'
                else:
                    action = 'REVIEW'
                    primary_reason = reason

                decisions.append(DecisionRecord(
                    source_event_id=sid, source=rec['source'],
                    amount_minor_units=rec['amount_minor_units'],
                    currency=rec['currency'],
                    action=action, primary_reason=primary_reason,
                    control_result='N/A', chosen_candidate_sid=None,
                    confidence=top.get('probabilistic_confidence'),
                    risk_exposure_score=self._risk(rec, action),
                    llm_provider=provider_audit
                ))
                processed_sids.add(sid)
                continue

            # Run controls over proposed allocation
            if 'F_VERIFIER' in self.disabled_stages:
                failed = []
            else:
                ctrl_ctx = self._build_control_context(rec, cand_rec, allocated_sids)
                ctrl_results = self.controls.run_all(ctrl_ctx)
                failed = [r for r in ctrl_results if r.status == 'FAIL']

            if failed:
                decisions.append(DecisionRecord(
                    source_event_id=sid, source=rec['source'],
                    amount_minor_units=rec['amount_minor_units'],
                    currency=rec['currency'],
                    action='REVIEW',
                    primary_reason='CONTROL_FAIL',
                    control_result='FAIL: ' + ','.join(r.control_id for r in failed),
                    chosen_candidate_sid=top['candidate_source_record_id'],
                    confidence=top.get('probabilistic_confidence'),
                    risk_exposure_score=self._risk(rec, 'REVIEW'),
                    llm_provider=provider_audit
                ))
            else:
                decisions.append(DecisionRecord(
                    source_event_id=sid, source=rec['source'],
                    amount_minor_units=rec['amount_minor_units'],
                    currency=rec['currency'],
                    action='MATCH',
                    primary_reason=top.get('deterministic_reason') if top.get('deterministic_match') else 'CANDIDATE_MATCH',
                    control_result='PASS',
                    chosen_candidate_sid=top['candidate_source_record_id'],
                    confidence=1.0 if top.get('deterministic_match') else top.get('probabilistic_confidence'),
                    risk_exposure_score=None,
                    llm_provider=provider_audit
                ))
                allocated_sids.add(sid)
                allocated_sids.add(top['candidate_source_record_id'])

            processed_sids.add(sid)

        # Records with no candidates from blocking and not yet processed
        remaining = [r for r in unresolved
                     if r['source_record_id'] not in processed_sids
                     and r['source_record_id'] not in resolved_sids]
        for rec in remaining:
            # P0: PENDING semantics are based on lifecycle/settlement window when there are no matches.
            lifecycle = rec.get('lifecycle_state', '')
            if lifecycle in ('INITIATED', 'CAPTURED', 'PARTIALLY_SETTLED'):
                action = 'PENDING'
                primary_reason = 'LIFECYCLE_PENDING_SETTLEMENT'
            else:
                action = 'NO_MATCH'
                primary_reason = 'NO_CANDIDATE'

            decisions.append(DecisionRecord(
                source_event_id=rec['source_record_id'],
                source=rec['source'],
                amount_minor_units=rec['amount_minor_units'],
                currency=rec['currency'],
                action=action, primary_reason=primary_reason,
                control_result='N/A', chosen_candidate_sid=None,
                confidence=None, risk_exposure_score=self._risk(rec, action),
            ))

        return PipelineResult(
            run_seed=seed,
            total_source_records=total,
            accepted=total,
            deduplicated=0,
            rejected=0,
            naive_comparison_count=naive_count,
            candidate_pair_count=candidate_count,
            blocking_reduction_factor=reduction,
            decisions=decisions,
        )

    def _build_control_context(self, rec: dict, cand: dict, allocated_sids: set) -> dict:
        """Builds a minimal control context from two records being proposed for matching."""
        ctx: dict = {}
        ctx['proposed_allocation_lines'] = [
            {'source_record_id': rec['source_record_id']},
            {'source_record_id': cand['source_record_id']},
        ]
        ctx['existing_allocated_ids'] = allocated_sids
        ctx['currencies'] = [rec.get('currency', 'INR'), cand.get('currency', 'INR')]
        ctx['source_a'] = rec.get('source')
        ctx['source_b'] = cand.get('source')
        ctx['proposed_source_record_ids'] = {rec['source_record_id'], cand['source_record_id']}
        ctx['deduplicated_source_event_ids'] = set()

        # Gateway facts from raw_payload
        gw_record = rec if rec.get('source') == 'GATEWAY' else (
            cand if cand.get('source') == 'GATEWAY' else None
        )
        if gw_record:
            payload = gw_record.get('raw_payload', {})
            ctx['gateway_gross_minor'] = payload.get('gateway_gross_minor', 0)
            ctx['gateway_fee_minor'] = payload.get('gateway_fee_minor', 0)
            ctx['gateway_tax_minor'] = payload.get('gateway_tax_minor', 0)
            ctx['gateway_net_minor'] = gw_record.get('amount_minor_units', 0)

        bank_record = rec if rec.get('source') == 'BANK' else (
            cand if cand.get('source') == 'BANK' else None
        )
        if bank_record and gw_record:
            ctx['bank_credit_minor'] = bank_record.get('amount_minor_units', 0)

        return ctx

    def _build_group_control_context(self, group_recs: list, allocated_sids: set) -> dict:
        ctx = {}
        ctx['proposed_allocation_lines'] = [{'source_record_id': r['source_record_id']} for r in group_recs]
        ctx['existing_allocated_ids'] = allocated_sids
        ctx['currencies'] = [r.get('currency', 'INR') for r in group_recs]
        sources = [r.get('source') for r in group_recs]
        ctx['source_a'] = sources[0] if len(sources) > 0 else None
        ctx['source_b'] = sources[1] if len(sources) > 1 else None
        ctx['proposed_source_record_ids'] = {r['source_record_id'] for r in group_recs}
        ctx['deduplicated_source_event_ids'] = set()
        gw_records = [r for r in group_recs if r.get('source') == 'GATEWAY']
        if gw_records:
            payload = gw_records[0].get('raw_payload', {})
            ctx['gateway_gross_minor'] = payload.get('gateway_gross_minor', 0)
            ctx['gateway_fee_minor'] = payload.get('gateway_fee_minor', 0)
            ctx['gateway_tax_minor'] = payload.get('gateway_tax_minor', 0)
            ctx['gateway_net_minor'] = gw_records[0].get('amount_minor_units', 0)
        bank_records = [r for r in group_recs if r.get('source') == 'BANK']
        if bank_records and gw_records:
            ctx['bank_credit_minor'] = bank_records[0].get('amount_minor_units', 0)
        return ctx

    def _risk(self, rec: dict, action: str) -> float:
        """
        Heuristic risk exposure score: exposure × uncertainty × modifier.
        Explicitly labeled as heuristic — not a calibrated probability.
        """
        exposure = rec.get('amount_minor_units', 0) / 100.0  # convert paise to rupees
        uncertainty = {'NO_MATCH': 1.0, 'REVIEW': 0.7, 'PENDING': 0.3, 'MATCH': 0.0}.get(action, 0.5)
        return round(exposure * uncertainty, 2)
