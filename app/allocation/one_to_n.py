class OneToNAllocator:
    """
    Bounded subset-sum DP for 1:N (one settlement covers N invoices) or N:1.

    Explicit bounds (from config, with safe defaults):
      MAX_CANDIDATES = 5    (max invoice candidates for one settlement)
      MAX_SUBSET_SIZE = 4   (max subset size to consider)
      AMOUNT_TOLERANCE = 100 minor units
    """

    def __init__(self, config: dict):
        self.config = config
        alloc_config = config.get('allocation', {})
        self.max_candidates = alloc_config.get('max_candidates', 5)
        self.max_subset_size = alloc_config.get('max_subset_size', 4)
        self.amount_tolerance = alloc_config.get('amount_tolerance', 100)

    def _dp_subset_sum(self, target: int, amounts: list[tuple[str, int]], tolerance: int) -> list[str] | None:
        """Returns list of matching source_record_ids or None if no match within tolerance."""
        # States: dictionary mapping subset_sum to list of record_ids
        states = {0: []}
        
        for record_id, amt in amounts:
            new_states = {}
            for current_sum, current_subset in states.items():
                if len(current_subset) >= self.max_subset_size:
                    continue
                new_sum = current_sum + amt
                new_subset = current_subset + [record_id]
                
                if new_sum not in states:
                    new_states[new_sum] = new_subset
            
            states.update(new_states)
            
            # Early exit if we find a match
            for current_sum, current_subset in states.items():
                if current_sum > 0 and abs(current_sum - target) <= tolerance:
                    return current_subset
                    
        return None

    def allocate(self, settlement_record: dict, invoice_candidates: list[dict]) -> dict:
        """
        Find the smallest subset of invoice_candidates whose total amount_minor_units
        is within AMOUNT_TOLERANCE of settlement_record['amount_minor_units'].
        """
        if len(invoice_candidates) > self.max_candidates:
            return {
                'found': False,
                'matched_records': [],
                'total_matched_minor': 0,
                'residual_minor': settlement_record.get('amount_minor_units', 0),
                'route_to_review': True,
                'review_reason': f'Candidates exceeded max limit: {len(invoice_candidates)} > {self.max_candidates}'
            }
            
        target_amount = settlement_record.get('amount_minor_units', 0)
        amounts = [(c['source_record_id'], c.get('amount_minor_units', 0)) for c in invoice_candidates]
        
        matched_subset = self._dp_subset_sum(target_amount, amounts, self.amount_tolerance)
        
        if matched_subset:
            total_matched = sum(c.get('amount_minor_units', 0) for c in invoice_candidates if c['source_record_id'] in matched_subset)
            residual = abs(target_amount - total_matched)
            return {
                'found': True,
                'matched_records': matched_subset,
                'total_matched_minor': total_matched,
                'residual_minor': residual,
                'route_to_review': False,
                'review_reason': None
            }
            
        return {
            'found': False,
            'matched_records': [],
            'total_matched_minor': 0,
            'residual_minor': target_amount,
            'route_to_review': True,
            'review_reason': 'No subset matched within tolerance'
        }
