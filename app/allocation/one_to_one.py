import scipy.optimize
import numpy as np

class OneToOneAllocator:
    def __init__(self, config: dict):
        self.config = config
        self.auto_match_threshold = config.get('allocation', {}).get('auto_match_threshold', 0.8)

    def _filter_eligible(self, candidates: list[dict]) -> list[dict]:
        """Pre-threshold filter. Only candidates above auto_match_threshold enter assignment."""
        return [c for c in candidates if c.get('probabilistic_confidence', 0) >= self.auto_match_threshold]

    def allocate(self, candidates: list[dict]) -> list[dict]:
        """
        Input: list of candidate dicts, each has:
          source_record_id, candidate_source_record_id, probabilistic_confidence,
          source, amount_minor_units, currency (on the record side)
        """
        eligible = self._filter_eligible(candidates)
        if len(eligible) < 2:
            return []

        # Build matrices for Hungarian algorithm
        sources = list(set(c['source_record_id'] for c in eligible))
        targets = list(set(c['candidate_source_record_id'] for c in eligible))
        
        source_idx = {sid: i for i, sid in enumerate(sources)}
        target_idx = {tid: i for i, tid in enumerate(targets)}

        cost_matrix = np.ones((len(sources), len(targets))) * 2.0  # high cost default

        for c in eligible:
            i = source_idx[c['source_record_id']]
            j = target_idx[c['candidate_source_record_id']]
            # cost is 1 - confidence
            cost = 1.0 - c.get('probabilistic_confidence', 0)
            if cost < cost_matrix[i, j]:
                cost_matrix[i, j] = cost

        row_ind, col_ind = scipy.optimize.linear_sum_assignment(cost_matrix)

        allocations = []
        for i, j in zip(row_ind, col_ind):
            cost = cost_matrix[i, j]
            if cost <= 1.0: # Meaning it was actually found in candidates
                # Find the candidate dictionary
                matched_candidate = None
                for c in eligible:
                    if c['source_record_id'] == sources[i] and c['candidate_source_record_id'] == targets[j]:
                        matched_candidate = c
                        break
                
                if matched_candidate:
                    allocations.append({
                        'allocation_type': 'ONE_TO_ONE',
                        'source_record_id': sources[i],
                        'matched_source_record_id': targets[j],
                        'confidence': matched_candidate.get('probabilistic_confidence', 0),
                        'amount_minor_units': matched_candidate.get('amount_minor_units', 0),
                        'currency': matched_candidate.get('currency', 'UNK')
                    })
        
        return allocations
