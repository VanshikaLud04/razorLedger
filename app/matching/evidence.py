import math

EVIDENCE_FAMILIES = {
    'NUMERIC': ['amount_agreement', 'amount_difference_bin'],
    'TEMPORAL': ['date_delta_bin'],
    'IDENTITY': ['reference_similarity_bin', 'counterparty_similarity_bin'],
    'SEMANTIC': ['description_similarity_bin'],
    'SOURCE': ['source_compatibility'],
}

def compute_rarity_frequencies(records: list[dict]) -> dict:
    freqs = {}
    total = 0
    for r in records:
        ref = r.get('reference')
        if ref:
            norm = ref.upper().replace(' ', '').replace('-', '')
            freqs[norm] = freqs.get(norm, 0) + 1
            total += 1
    freqs['__total__'] = total
    return freqs

class EvidenceFeatureBuilder:
    def __init__(self, config: dict, rarity_frequencies: dict | None = None):
        self.config = config
        self.rarity_frequencies = rarity_frequencies or {}
        
    def _rarity_score(self, ref_a: str | None, ref_b: str | None) -> float:
        if not ref_a or not ref_b or not self.rarity_frequencies:
            return 0.0
        norm_a = ref_a.upper().replace(' ', '').replace('-', '')
        norm_b = ref_b.upper().replace(' ', '').replace('-', '')
        if norm_a != norm_b:
            return 0.0
        freq = self.rarity_frequencies.get(norm_a, 1)
        total = self.rarity_frequencies.get('__total__', max(len(self.rarity_frequencies), 1))
        return -math.log2(freq / total) if freq > 0 else 0.0

    def build(self, record_a: dict, record_b: dict, fuzzy_scores: dict, deterministic: dict) -> dict:
        cfg = self.config.get('matching', {})
        evidence_cfg = self.config.get('evidence', {})
        
        amt_tolerance = cfg.get('amount_tolerance_minor', 0)
        amount_bins = evidence_cfg.get('amount_bins', {'near': 100, 'close': 500})
        date_bins = evidence_cfg.get('date_bins', {'near': 1, 'close': 3})
        ref_bins = evidence_cfg.get('reference_bins', {'exact': 0.95, 'high': 0.85, 'medium': 0.70})
        cp_bins = evidence_cfg.get('counterparty_bins', {'high': 0.85, 'medium': 0.70})

        delta = abs(record_a.get('amount_minor_units', 0) - record_b.get('amount_minor_units', 0))
        amount_agreement = delta <= amt_tolerance
        if delta == 0:
            amount_difference_bin = 'EXACT'
        elif delta <= amount_bins.get('near', 0):
            amount_difference_bin = 'NEAR'
        elif delta <= amount_bins.get('close', 0):
            amount_difference_bin = 'CLOSE'
        else:
            amount_difference_bin = 'FAR'
            
        date_delta = abs((record_a['transaction_date'] - record_b['transaction_date']).days)
        if date_delta == 0:
            date_delta_bin = 'SAME_DAY'
        elif date_delta <= date_bins.get('near', 0):
            date_delta_bin = 'NEAR'
        elif date_delta <= date_bins.get('close', 0):
            date_delta_bin = 'CLOSE'
        else:
            date_delta_bin = 'FAR'
            
        ref_score = fuzzy_scores.get('reference_similarity_score', 0.0)
        if deterministic.get('is_exact_reference_match'):
            reference_similarity_bin = 'EXACT'
        elif ref_score >= ref_bins.get('exact', 0.95):
            reference_similarity_bin = 'EXACT'
        elif ref_score >= ref_bins.get('high', 0.85):
            reference_similarity_bin = 'HIGH'
        elif ref_score >= ref_bins.get('medium', 0.70):
            reference_similarity_bin = 'MEDIUM'
        else:
            reference_similarity_bin = 'LOW'
            
        cp_score = fuzzy_scores.get('counterparty_similarity_score', 0.0)
        if cp_score >= cp_bins.get('high', 0.85):
            counterparty_similarity_bin = 'HIGH'
        elif cp_score >= cp_bins.get('medium', 0.70):
            counterparty_similarity_bin = 'MEDIUM'
        else:
            counterparty_similarity_bin = 'LOW'
            
        description_similarity_bin = 'LOW'
        semantic_similarity_score = 0.0
        
        valid_pairs = {('BANK','INVOICE'),('BANK','GATEWAY'),('INVOICE','GATEWAY'),
                       ('INVOICE','BANK'),('GATEWAY','BANK'),('GATEWAY','INVOICE')}
        source_compatibility = (record_a.get('source'), record_b.get('source')) in valid_pairs
        
        evidence_rarity_score = self._rarity_score(record_a.get('reference'), record_b.get('reference'))
        
        families_present = []
        if amount_agreement or amount_difference_bin in ('EXACT', 'NEAR'):
            families_present.append('NUMERIC')
        if date_delta_bin in ('SAME_DAY', 'NEAR', 'CLOSE'):
            families_present.append('TEMPORAL')
        if reference_similarity_bin in ('EXACT', 'HIGH') or counterparty_similarity_bin in ('HIGH',):
            families_present.append('IDENTITY')
        if semantic_similarity_score >= 0.80:
            families_present.append('SEMANTIC')
        if source_compatibility:
            families_present.append('SOURCE')
            
        return {
            'amount_agreement': amount_agreement,
            'amount_difference_bin': amount_difference_bin,
            'date_delta_bin': date_delta_bin,
            'reference_similarity_bin': reference_similarity_bin,
            'reference_similarity_score': ref_score,
            'counterparty_similarity_bin': counterparty_similarity_bin,
            'counterparty_similarity_score': cp_score,
            'description_similarity_bin': description_similarity_bin,
            'semantic_similarity_score': semantic_similarity_score,
            'source_compatibility': source_compatibility,
            'evidence_rarity_score': evidence_rarity_score,
            'evidence_families_present': list(set(families_present)),
        }
