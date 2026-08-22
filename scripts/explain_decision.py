import sys
import os
import pathlib
import copy
import logging

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')

from generator.config import GeneratorConfig, PARTITION_SEEDS
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver
from app.matching.evidence import compute_rarity_frequencies
from app.pipeline import ReconciliationPipeline

def explain(target_sid: str, partition: str = 'DEV'):
    seed = PARTITION_SEEDS.get(partition)
    if not seed:
        print(f"Unknown partition {partition}")
        return
        
    cfg = GeneratorConfig(seed=seed, partition=partition)
    events = EconomicEventGenerator(cfg).generate()
    deriver = SourceViewDeriver(cfg)
    raw_records, _ = deriver.derive(events)

    seen_sids = set()
    clean_records = []
    target_record = None

    for rec in raw_records:
        r = copy.copy(rec)
        r.pop('ground_truth_group_id', None)
        key = (r['source'], r['source_event_id'])
        if key in seen_sids:
            continue
        seen_sids.add(key)
        sid = f"{r['source']}-{r['source_event_id']}"
        r.setdefault('source_record_id', sid)
        clean_records.append(r)
        
        if sid == target_sid:
            target_record = r

    if not target_record:
        print(f"Record {target_sid} not found in partition {partition}.")
        return

    rarity = compute_rarity_frequencies(clean_records)
    pipeline = ReconciliationPipeline(rarity_frequencies=rarity)
    
    # We want to trace. We will run the pipeline, but we will introspect its components
    print(f"\n{'═'*60}")
    print(f"  RazorLedger — Audit & Explainability Trace")
    print(f"{'═'*60}")
    
    print("\n[1] SOURCE RECORD")
    for k, v in target_record.items():
        if not k.startswith('_'):
            print(f"    {k}: {v}")
            
    # Run full pipeline to get final decision and controls
    result = pipeline.run(clean_records, seed=seed)
    
    my_decision = next((d for d in result.decisions if d.source_event_id == target_sid), None)
    my_allocation = None
    
    if my_decision and my_decision.action == 'MATCH' and my_decision.primary_reason == 'DETERMINISTIC_EXACT':
        print(f"\n[2] DECISION: Auto-resolved in DETERMINISTIC phase")
    else:
        # Simulate blocking just to show candidates
        print(f"\n[2] BLOCKING")
        cands = pipeline.blocker.block(target_record, clean_records)
        print(f"    Candidates retrieved: {len(cands)}")
        for c in cands:
            print(f"      - {c['source_record_id']}")
            
        if not cands:
            print("\n[3] DECISION: NO_MATCH (No candidates found)")
        else:
            print("\n[3] EVIDENCE & SCORING")
            candidate_evidences = []
            for cand_record in cands:
                ev = pipeline.evb.build(target_record, cand_record)
                sem = pipeline.semantic.build(target_record, cand_record)
                ev.update(sem)
                ev['_cand_record'] = cand_record
                candidate_evidences.append(ev)
                
            ranked = pipeline.scorer.rank_candidates(target_sid, candidate_evidences)
            for i, c in enumerate(ranked):
                cand_id = c['_cand_record']['source_record_id']
                conf = c.get('probabilistic_confidence', 0.0)
                gap = c.get('confidence_gap_to_next', 0.0)
                print(f"    Candidate {i+1}: {cand_id}")
                print(f"      Confidence : {conf:.4f}")
                if i == 0:
                    print(f"      Gap to next: {gap:.4f}")
                print(f"      Evidence   :")
                for k, v in c.items():
                    if not k.startswith('_') and k not in ('probabilistic_confidence', 'confidence_gap_to_next'):
                        print(f"        {k}: {v}")
                        
            # Check AMBIGUITY GATE
            top = ranked[0]
            conf = top.get('probabilistic_confidence', 0.0)
            gap = top.get('confidence_gap_to_next', 0.0)
            print("\n[4] AMBIGUITY GATE")
            if pipeline.llm.should_invoke(ranked, 0):
                print(f"    Status: PASSED (conf {conf:.4f} >= 0.60, gap {gap:.4f} < 0.10)")
                print(f"    Action: Queued for LLM Evidence")
            else:
                print(f"    Status: EXCLUDED")
                if conf < 0.60:
                    print(f"    Reason: Confidence {conf:.4f} below 0.60 threshold")
                else:
                    print(f"    Reason: Gap {gap:.4f} >= 0.10 threshold (clear winner)")

    print("\n[5] ALLOCATION & CONTROLS")
    if my_decision and my_decision.control_result:
        print(f"    Control Result: {my_decision.control_result}")
    else:
        print("    No allocation created.")

    print("\n[6] FINAL DECISION")
    if my_decision:
        print(f"    Action: {my_decision.action}")
        print(f"    Reason: {my_decision.primary_reason}")
        print(f"    Matched to: {my_decision.chosen_candidate_sid}")
    else:
        print("    No decision found.")

    print(f"{'═'*60}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python explain_decision.py <source_record_id> [partition]")
        print("Example: python explain_decision.py INVOICE-INV-2023-000001-INV DEV")
        sys.exit(1)
        
    sid = sys.argv[1]
    part = sys.argv[2] if len(sys.argv) > 2 else 'DEV'
    explain(sid, part)
