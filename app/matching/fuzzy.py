# pyrefly: ignore [missing-import]
from rapidfuzz import fuzz
# pyrefly: ignore [missing-import]
from rapidfuzz.distance import JaroWinkler

class FuzzyMatcher:
    def __init__(self, config: dict):
        self.config = config
        
    def score(self, record_a: dict, record_b: dict) -> dict:
        def norm_str(s):
            if not s:
                return None
            return str(s).lower().replace(' ', '').replace('-', '').replace('_', '').replace('.', '')
            
        ref_a = norm_str(record_a.get('reference'))
        ref_b = norm_str(record_b.get('reference'))
        
        scores = {
            'reference_levenshtein': 0.0,
            'reference_jaro_winkler': 0.0,
            'reference_token_sort': 0.0,
            'reference_partial': 0.0,
            'counterparty_levenshtein': 0.0,
            'counterparty_jaro_winkler': 0.0,
            'counterparty_token_sort': 0.0,
        }
        
        if ref_a and ref_b:
            scores['reference_levenshtein'] = fuzz.ratio(ref_a, ref_b)
            scores['reference_jaro_winkler'] = JaroWinkler.normalized_similarity(ref_a, ref_b) * 100.0
            scores['reference_token_sort'] = fuzz.token_sort_ratio(ref_a, ref_b)
            scores['reference_partial'] = fuzz.partial_ratio(ref_a, ref_b)
            
        cp_a = norm_str(record_a.get('counterparty'))
        cp_b = norm_str(record_b.get('counterparty'))
        
        if cp_a and cp_b:
            scores['counterparty_levenshtein'] = fuzz.ratio(cp_a, cp_b)
            scores['counterparty_jaro_winkler'] = JaroWinkler.normalized_similarity(cp_a, cp_b) * 100.0
            scores['counterparty_token_sort'] = fuzz.token_sort_ratio(cp_a, cp_b)
            
        ref_scores = [
            scores['reference_levenshtein'],
            scores['reference_jaro_winkler'],
            scores['reference_token_sort']
        ]
        composite_ref = max(ref_scores) / 100.0 if ref_scores else 0.0
        
        cp_scores = [
            scores['counterparty_levenshtein'],
            scores['counterparty_jaro_winkler'],
            scores['counterparty_token_sort']
        ]
        composite_cp = max(cp_scores) / 100.0 if cp_scores else 0.0
        
        desc_a = norm_str(record_a.get('description'))
        desc_b = norm_str(record_b.get('description'))
        composite_desc = 0.0
        if desc_a and desc_b:
            # Using token_set_ratio which handles prefixes like "Invoice: " and "Gateway settlement: " effectively
            composite_desc = fuzz.token_set_ratio(desc_a, desc_b) / 100.0
        
        scores['reference_similarity_score'] = composite_ref
        scores['counterparty_similarity_score'] = composite_cp
        scores['description_similarity_score'] = composite_desc
        
        return scores
