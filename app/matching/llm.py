class LLMEvidenceGenerator:
    def __init__(self, config: dict):
        self.config = config

    def should_invoke(self, top_candidates: list[dict], calls_used: int) -> bool:
        max_calls = self.config.get('llm', {}).get('max_calls_per_run', 3)
        if calls_used >= max_calls:
            return False
        if len(top_candidates) < 2:
            return False
        gap = top_candidates[0].get('confidence_gap_to_next', 1.0)
        return gap < 0.10

    def generate(self, source_record: dict, top_candidates: list[dict]) -> dict:
        return {
            'llm_invoked': False,
            'llm_semantic_assessment': None,
            'llm_supporting_evidence': None,
            'llm_contradicting_evidence': None,
            'llm_stated_uncertainty': 'LLM_NOT_IMPLEMENTED_YET',
            'route_to_review': True,
        }
