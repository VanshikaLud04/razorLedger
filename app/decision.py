class DecisionEngine:
    def __init__(self, config: dict, scorer=None, control_engine=None):
        self.config = config
        self.scorer = scorer
        self.control_engine = control_engine
        
        alloc_config = config.get('allocation', {})
        self.auto_match_threshold = alloc_config.get('auto_match_threshold', 0.8)
        self.review_threshold = alloc_config.get('review_threshold', 0.4)
        self.min_confidence_gap = alloc_config.get('minimum_confidence_gap', 0.1)

    def _risk_exposure(self, source_record: dict, reason: str, action: str, control_failed: bool) -> float:
        """
        Heuristic: exposure × uncertainty × modifier.
        """
        amount = source_record.get('amount_minor_units', 0)
        exposure = amount / 100.0  # in rupees
        
        uncertainty = 1.0
        if action == 'REVIEW':
            uncertainty = 0.7
        elif action == 'PENDING':
            uncertainty = 0.3
            
        modifier = 1.2 if control_failed else 1.0
        
        return exposure * uncertainty * modifier

    def decide(
        self,
        source_record: dict,
        ranked_candidates: list[dict],
        allocation_context: dict,
        existing_allocated_ids: set[str],
        settlement_window_days: int
    ) -> dict:
        
        if not ranked_candidates:
            action = 'NO_MATCH'
            # Assuming older than settlement_window_days would be NO_MATCH, else PENDING
            # We don't have transaction_date here, but based on prompt logic:
            if allocation_context.get('days_old', 0) <= settlement_window_days:
                action = 'PENDING'
                
            return {
                'action': action,
                'primary_reason': 'NO_CANDIDATE',
                'control_result': 'PASS',
                'chosen_candidate_id': None,
                'risk_exposure_score': self._risk_exposure(source_record, 'NO_CANDIDATE', action, False),
                'control_details': []
            }

        top_candidate = ranked_candidates[0]
        confidence = top_candidate.get('probabilistic_confidence', 0)
        
        if confidence < self.review_threshold:
            action = 'PENDING' if allocation_context.get('days_old', 0) <= settlement_window_days else 'NO_MATCH'
            return {
                'action': action,
                'primary_reason': 'BELOW_REVIEW_THRESHOLD',
                'control_result': 'PASS',
                'chosen_candidate_id': None,
                'risk_exposure_score': self._risk_exposure(source_record, 'BELOW_REVIEW_THRESHOLD', action, False),
                'control_details': []
            }

        # Check gap
        if len(ranked_candidates) > 1:
            second_confidence = ranked_candidates[1].get('probabilistic_confidence', 0)
            if (confidence - second_confidence) < self.min_confidence_gap:
                return {
                    'action': 'REVIEW',
                    'primary_reason': 'CONFIDENCE_GAP_TOO_SMALL',
                    'control_result': 'PASS',
                    'chosen_candidate_id': top_candidate.get('candidate_id'),
                    'risk_exposure_score': self._risk_exposure(source_record, 'GAP', 'REVIEW', False),
                    'control_details': []
                }
                
        if confidence < self.auto_match_threshold:
            return {
                'action': 'REVIEW',
                'primary_reason': 'BELOW_AUTO_MATCH_THRESHOLD',
                'control_result': 'PASS',
                'chosen_candidate_id': top_candidate.get('candidate_id'),
                'risk_exposure_score': self._risk_exposure(source_record, 'THRESHOLD', 'REVIEW', False),
                'control_details': []
            }

        # Controls check
        if self.control_engine:
            control_results = self.control_engine.run_all(allocation_context)
            failed_controls = [r for r in control_results if r.status == 'FAIL']
            
            if failed_controls:
                failed_ids = ",".join([r.control_id for r in failed_controls])
                return {
                    'action': 'REVIEW',
                    'primary_reason': 'CONTROL_FAILURE',
                    'control_result': f'FAIL: {failed_ids}',
                    'chosen_candidate_id': top_candidate.get('candidate_id'),
                    'risk_exposure_score': self._risk_exposure(source_record, 'CONTROL', 'REVIEW', True),
                    'control_details': control_results
                }
                
        return {
            'action': 'MATCH',
            'primary_reason': 'AUTO_MATCH',
            'control_result': 'PASS',
            'chosen_candidate_id': top_candidate.get('candidate_id'),
            'risk_exposure_score': self._risk_exposure(source_record, 'MATCH', 'MATCH', False),
            'control_details': []
        }
