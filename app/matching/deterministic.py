class DeterministicMatcher:
    def __init__(self, config: dict):
        self.config = config

    def match(self, record_a: dict, record_b: dict) -> dict:
        def norm_ref(r):
            if not r:
                return None
            return r.upper().replace(' ', '').replace('-', '')
            
        ref_a = norm_ref(record_a.get('reference'))
        ref_b = norm_ref(record_b.get('reference'))
        
        is_exact_reference_match = False
        if ref_a and ref_b and ref_a == ref_b:
            is_exact_reference_match = True
            
        amt_a = record_a.get('amount_minor_units')
        amt_b = record_b.get('amount_minor_units')
        date_a = record_a.get('transaction_date')
        date_b = record_b.get('transaction_date')
        
        is_exact_amount_date_match = False
        if amt_a is not None and amt_b is not None and amt_a == amt_b:
            if date_a is not None and date_b is not None and date_a == date_b:
                is_exact_amount_date_match = True
                
        deterministic_match = is_exact_reference_match
        
        if is_exact_reference_match:
            match_type = 'EXACT_REFERENCE'
        else:
            match_type = 'NONE'
            
        return {
            'is_exact_reference_match': is_exact_reference_match,
            'is_exact_amount_date_match': is_exact_amount_date_match,
            'deterministic_match': deterministic_match,
            'match_type': match_type
        }
