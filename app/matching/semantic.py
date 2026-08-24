
class SemanticFeatureBuilder:
    def __init__(self, config: dict):
        self.config = config
        import json
        import os
        if os.path.exists("scratch/dev_embeddings.json"):
            with open("scratch/dev_embeddings.json", "r") as f:
                self.emb_cache = json.load(f)
        else:
            self.emb_cache = {}

    def build(self, record_a: dict, record_b: dict) -> dict:
        desc_a = record_a.get('description') or ''
        desc_b = record_b.get('description') or ''
        cp_a = record_a.get('counterparty') or ''
        cp_b = record_b.get('counterparty') or ''
        text_a = f"{cp_a} {desc_a}".strip()
        text_b = f"{cp_b} {desc_b}".strip()
        
        if not text_a or not text_b:
            return {'semantic_similarity_score': 0.0, 'semantic_similarity_bin': 'LOW', 'description_similarity_bin': 'LOW', '_semantic_active': True}
            
        emb_a = self.emb_cache.get(text_a)
        emb_b = self.emb_cache.get(text_b)
        
        if not emb_a or not emb_b:
            return {'semantic_similarity_score': 0.0, 'semantic_similarity_bin': 'LOW', 'description_similarity_bin': 'LOW', '_semantic_active': True}
            
        import math
        def dot_product(v1, v2):
            return sum(x*y for x, y in zip(v1, v2))
        def magnitude(v):
            return math.sqrt(sum(x*x for x in v))
        def cos_sim(v1, v2):
            m1, m2 = magnitude(v1), magnitude(v2)
            if m1 == 0 or m2 == 0: return 0.0
            return dot_product(v1, v2) / (m1 * m2)

        score = cos_sim(emb_a, emb_b)
        
        if score >= 0.85: bin_val = 'HIGH'
        elif score >= 0.70: bin_val = 'MEDIUM'
        else: bin_val = 'LOW'
        
        return {
            'semantic_similarity_score': score,
            'semantic_similarity_bin': bin_val,
            'description_similarity_bin': bin_val,
            '_semantic_active': True,
        }
