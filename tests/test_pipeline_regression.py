import sys
import types

mock_groq = types.ModuleType("groq")
mock_groq.Groq = lambda *args, **kwargs: None
sys.modules["groq"] = mock_groq

mock_genai = types.ModuleType("google.genai")
mock_genai.Client = lambda *args, **kwargs: None
sys.modules["google.genai"] = mock_genai

mock_genai_types = types.ModuleType("google.genai.types")
sys.modules["google.genai.types"] = mock_genai_types

from app.pipeline import ReconciliationPipeline
from app.matching.llm import LLMEvidenceGenerator, LLMAssessment
import datetime

class DummySemantic:
    def build(self, r, c):
        return {'semantic_similarity_score': 0.0, 'semantic_similarity_bin': 'LOW', 'description_similarity_bin': 'LOW', '_semantic_active': False}

def make_rec(sid, src, amt, state):
    return {
        'source_record_id': sid,
        'source': src,
        'amount_minor_units': amt,
        'currency': 'INR',
        'lifecycle_state': state,
        'transaction_date': datetime.date(2025, 1, 1),
        'counterparty': 'Test',
        'reference': 'Ref-1',
        'description': 'Desc-1'
    }

def test_llm_wiring_regression():
    pipeline = ReconciliationPipeline(rarity_frequencies={}); pipeline.det.match = lambda r, c: {"deterministic_match": False, "match_type": None}
    pipeline.semantic = DummySemantic()
    for k in list(pipeline.scorer.weights.keys()):
        if k.startswith('semantic_'):
            pipeline.scorer.weights[k] = 0.0
    for wk in pipeline.scorer.weights:
        pipeline.scorer.weights[wk] = 0.0
    pipeline.scorer.weights["amount_exact"] = 0.5
    pipeline.scorer.weights["amount_exact"] = 0.0
            
    pipeline.llm.should_invoke = lambda *a, **k: True
    
    def fake_generate_batch(batch_prompts, run_id):
        print("BATCH PROMPTS", batch_prompts)
        results = []
        for p in batch_prompts:
            sid = p['source_record']['source_record_id']
            results.append(LLMAssessment(
                group_id=sid,
                cand1_supporting_evidence="Good", cand1_contradicting_evidence="None",
                cand2_supporting_evidence="Bad", cand2_contradicting_evidence="Lot",
                comparative_preference="CANDIDATE_1_STRONGLY_PREFERRED",
                uncertainty_level="LOW"
            ))
        return results
        
    pipeline.llm.generate_batch = fake_generate_batch
    
    original_apply = pipeline.scorer.apply_llm_adjustment
    calls = []
    def hooked_apply(base, llm_ass):
        calls.append((base, llm_ass))
        return original_apply(base, llm_ass)
    pipeline.scorer.__class__.apply_llm_adjustment = lambda s, b, a: hooked_apply(b, a)
    
    records = [
        make_rec('REC-1', 'INVOICE', 1000, 'CAPTURED'),
        make_rec('CAND-1', 'BANK', 1000, 'SETTLED'),
        make_rec('CAND-2', 'GATEWAY', 2000, 'SETTLED'),
    ]
    
    res = pipeline.run(records, seed='test')
    
    assert len(calls) == 3
    assert calls[0][1] == 'supports', f"LLM semantic assessment mapped to {calls[0][1]}"
    
    dec = res.decisions[0]
    assert dec.action == 'MATCH' or dec.confidence > 0.0

def test_pending_routing_no_candidates_unsettled():
    pipeline = ReconciliationPipeline(rarity_frequencies={}); pipeline.det.match = lambda r, c: {"deterministic_match": False, "match_type": None}
    records = [make_rec('REC-1', 'INVOICE', 1000, 'CAPTURED')]
    res = pipeline.run(records, seed='test')
    assert res.decisions[0].action == 'PENDING'
    assert res.decisions[0].primary_reason == 'LIFECYCLE_PENDING_SETTLEMENT'

def test_pending_routing_no_candidates_settled():
    pipeline = ReconciliationPipeline(rarity_frequencies={}); pipeline.det.match = lambda r, c: {"deterministic_match": False, "match_type": None}
    records = [make_rec('REC-1', 'INVOICE', 1000, 'SETTLED')]
    res = pipeline.run(records, seed='test')
    assert res.decisions[0].action == 'NO_MATCH'
    assert res.decisions[0].primary_reason == 'NO_CANDIDATE'

def test_pending_routing_below_review_threshold_unsettled():
    pipeline = ReconciliationPipeline(rarity_frequencies={}); pipeline.det.match = lambda r, c: {"deterministic_match": False, "match_type": None}
    pipeline.semantic = DummySemantic()
    pipeline.scorer.weights = {k: 0.0 for k in pipeline.scorer.weights}
    
    records = [
        make_rec('REC-1', 'INVOICE', 1000, 'CAPTURED'),
        make_rec('CAND-1', 'BANK', 5000, 'SETTLED'),
    ]
    res = pipeline.run(records, seed='test')
    dec = next(d for d in res.decisions if d.source_event_id == 'REC-1')
    assert dec.action == 'PENDING'
    assert dec.primary_reason == 'LIFECYCLE_PENDING_SETTLEMENT'

def test_pending_routing_below_review_threshold_settled():
    pipeline = ReconciliationPipeline(rarity_frequencies={}); pipeline.det.match = lambda r, c: {"deterministic_match": False, "match_type": None}
    pipeline.semantic = DummySemantic()
    pipeline.scorer.weights = {k: 0.0 for k in pipeline.scorer.weights}
    records = [
        make_rec('REC-1', 'INVOICE', 1000, 'SETTLED'),
        make_rec('CAND-1', 'BANK', 5000, 'SETTLED'),
    ]
    res = pipeline.run(records, seed='test')
    dec = next(d for d in res.decisions if d.source_event_id == 'REC-1')
    assert dec.action == 'NO_MATCH'
    assert dec.primary_reason == 'BELOW_REVIEW_THRESHOLD'
