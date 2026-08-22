class EvidenceWeightedScorer:
    def __init__(self, config: dict):
        self.weights = {
            'amount_EXACT': 0.30,
            'amount_NEAR': 0.20,
            'amount_CLOSE': 0.08,
            'amount_FAR': -0.30,
            'date_SAME_DAY': 0.15,
            'date_NEAR': 0.10,
            'date_CLOSE': 0.05,
            'date_FAR': -0.30,
            'reference_EXACT': 0.35,
            'reference_HIGH': 0.20,
            'reference_MEDIUM': 0.05,
            'reference_LOW': -0.40,
            'counterparty_HIGH': 0.10,
            'counterparty_MEDIUM': 0.04,
            'counterparty_LOW': -0.10,
            'semantic_HIGH': 0.15,
            'semantic_MEDIUM': 0.05,
            'semantic_LOW': -0.10,
            'source_compatible': 0.05,
            'source_incompatible': -0.30,
            'rarity_weight': 0.05,
        }
        self.llm_max_delta = config.get('llm', {}).get('llm_max_evidence_delta', 0.20)
        self.min_families = config.get('evidence', {}).get('min_families_for_auto_match', 2)
        self.auto_match_threshold = config.get('matching', {}).get('auto_match_threshold', 0.80)
        self.review_threshold = config.get('matching', {}).get('review_threshold', 0.40)
        self.min_gap = config.get('matching', {}).get('minimum_confidence_gap', 0.15)
        
    def score_candidate(self, evidence: dict) -> float:
        if evidence.get('deterministic_match'):
            return 1.0
        
        raw = 0.30
        raw += self.weights.get(f"amount_{evidence.get('amount_difference_bin')}", 0)
        raw += self.weights.get(f"date_{evidence.get('date_delta_bin')}", 0)
        raw += self.weights.get(f"reference_{evidence.get('reference_similarity_bin')}", 0)
        raw += self.weights.get(f"counterparty_{evidence.get('counterparty_similarity_bin')}", 0)
        raw += self.weights.get(f"semantic_{evidence.get('semantic_similarity_bin')}", 0)
        
        if evidence.get('source_compatibility'):
            raw += self.weights['source_compatible']
        else:
            raw += self.weights['source_incompatible']
            
        # P0: Treat rarity weight explicitly as an uncalibrated temporary heuristic 
        # until a real informativeness model is built.
        raw += self.weights['rarity_weight'] * (evidence.get('evidence_rarity_score') or 0.0)
        
        return max(0.0, min(1.0, raw))

    def apply_llm_adjustment(self, base_score: float, llm_assessment: str | None) -> float:
        if llm_assessment == 'supports':
            adjusted = base_score + self.llm_max_delta
        elif llm_assessment == 'contradicts':
            adjusted = base_score - self.llm_max_delta
        else:
            adjusted = base_score
        return max(0.0, min(1.0, adjusted))

    def rank_candidates(self, source_record_id: str, candidate_evidences: list[dict]) -> list[dict]:
        scored = []
        for ev in candidate_evidences:
            score = self.score_candidate(ev)
            scored.append({**ev, 'probabilistic_confidence': score})
            
        scored.sort(key=lambda x: x['probabilistic_confidence'], reverse=True)
        
        for i, c in enumerate(scored):
            if i + 1 < len(scored):
                c['confidence_gap_to_next'] = c['probabilistic_confidence'] - scored[i+1]['probabilistic_confidence']
            else:
                c['confidence_gap_to_next'] = c['probabilistic_confidence']
                
        return scored

    def check_auto_match_eligibility(self, top_candidate: dict) -> tuple[bool, str]:
        conf = top_candidate.get('probabilistic_confidence', 0.0)
        gap = top_candidate.get('confidence_gap_to_next', 0.0)
        families = top_candidate.get('evidence_families_present', [])
        
        if conf < self.auto_match_threshold:
            return False, f'BELOW_THRESHOLD (confidence={conf:.3f})'
        if gap < self.min_gap:
            return False, f'CONFIDENCE_GAP_INSUFFICIENT (gap={gap:.3f})'
        if len(set(families)) < self.min_families:
            return False, f'INSUFFICIENT_EVIDENCE_FAMILIES ({families})'
        if not top_candidate.get('source_compatibility'):
            return False, 'SOURCE_INCOMPATIBLE'
            
        return True, 'ELIGIBLE'
