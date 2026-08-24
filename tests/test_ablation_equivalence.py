import sys
import types
import copy

mock_groq = types.ModuleType("groq")
mock_groq.Groq = lambda *args, **kwargs: None
sys.modules["groq"] = mock_groq

mock_genai = types.ModuleType("google.genai")
mock_genai.Client = lambda *args, **kwargs: None
sys.modules["google.genai"] = mock_genai

mock_genai_types = types.ModuleType("google.genai.types")
sys.modules["google.genai.types"] = mock_genai_types

from app.pipeline import ReconciliationPipeline
from generator.config import GeneratorConfig
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver
from app.matching.evidence import compute_rarity_frequencies

def test_ablation_default_equivalence():
    cfg = GeneratorConfig(seed="test_ablation", partition="DEV")
    events = EconomicEventGenerator(cfg).generate()
    raw_records, _ = SourceViewDeriver(cfg).derive(events)
    
    clean_records = []
    seen = set()
    for rec in raw_records:
        r = copy.copy(rec)
        r.pop('ground_truth_group_id', None)
        key = (r['source'], r['source_event_id'])
        if key in seen:
            continue
        seen.add(key)
        r['source_record_id'] = f"{r['source']}-{r['source_event_id']}"
        clean_records.append(r)
        
    rarity = compute_rarity_frequencies(clean_records)
    
    pipe_standard = ReconciliationPipeline(rarity_frequencies=rarity)
    result_standard = pipe_standard.run(copy.deepcopy(clean_records), seed="test_ablation")
    
    # We will pass disabled_stages once we implement it
    pipe_ablation = ReconciliationPipeline(rarity_frequencies=rarity, disabled_stages=set())
    result_ablation = pipe_ablation.run(copy.deepcopy(clean_records), seed="test_ablation")
    
    assert len(result_standard.decisions) == len(result_ablation.decisions)
    for d1, d2 in zip(result_standard.decisions, result_ablation.decisions):
        assert d1 == d2
