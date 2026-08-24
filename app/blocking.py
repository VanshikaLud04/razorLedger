import logging
import re
from datetime import timedelta

logger = logging.getLogger(__name__)

class CompoundBlocker:
    def __init__(self, config: dict):
        self.config = config.get('matching', {})
        self.date_tolerance_days = self.config.get('date_tolerance_days', 7)
    
    def _normalize_counterparty(self, s: str) -> str:
        if not s:
            return ""
        s = s.lower()
        s = re.sub(r'[^\w\s]', '', s)
        return s[:8]
    
    def _normalize_reference(self, s: str) -> str:
        if not s:
            return ""
        s = s.upper()
        s = s.replace(' ', '').replace('-', '')
        return s[:8]
    
    def _amount_bucket(self, amount: int) -> int:
        return (amount // 10000) * 10000

    def block(self, records: list[dict]) -> list[tuple[str, str]]:
        candidates = set()
        naive_comparison_count = len(records) * (len(records) - 1) // 2
        
        # Block A: amount bucket + settlement date window
        bucket_a = {}
        for r in records:
            amt_b = self._amount_bucket(r.get('amount_minor_units', 0))
            bucket_a.setdefault(amt_b, []).append(r)
            
        for amt_b, recs in bucket_a.items():
            for i in range(len(recs)):
                for j in range(i + 1, len(recs)):
                    r1 = recs[i]
                    r2 = recs[j]
                    if r1.get('source') == r2.get('source'):
                        continue
                    delta_days = abs((r1['transaction_date'] - r2['transaction_date']).days)
                    if delta_days <= self.date_tolerance_days:
                        id1, id2 = sorted([r1['source_record_id'], r2['source_record_id']])
                        candidates.add((id1, id2))
        
        # Block B: normalized counterparty prefix + amount bucket
        bucket_b = {}
        for r in records:
            cp = self._normalize_counterparty(r.get('counterparty', ''))
            amt_b = self._amount_bucket(r.get('amount_minor_units', 0))
            if cp:
                bucket_b.setdefault((cp, amt_b), []).append(r)
                
        for (cp, amt_b), recs in bucket_b.items():
            for i in range(len(recs)):
                for j in range(i + 1, len(recs)):
                    r1 = recs[i]
                    r2 = recs[j]
                    if r1.get('source') == r2.get('source'):
                        continue
                    id1, id2 = sorted([r1['source_record_id'], r2['source_record_id']])
                    candidates.add((id1, id2))
                    
        # Block C: reference prefix/suffix + source compatibility
        valid_pairs = {('BANK','INVOICE'), ('BANK','GATEWAY'), ('INVOICE','GATEWAY'),
                       ('INVOICE','BANK'), ('GATEWAY','BANK'), ('GATEWAY','INVOICE')}
        bucket_c = {}
        for r in records:
            ref = self._normalize_reference(r.get('reference', ''))
            if ref:
                bucket_c.setdefault(ref, []).append(r)
                
        for ref, recs in bucket_c.items():
            for i in range(len(recs)):
                for j in range(i + 1, len(recs)):
                    r1 = recs[i]
                    r2 = recs[j]
                    if (r1.get('source'), r2.get('source')) in valid_pairs:
                        id1, id2 = sorted([r1['source_record_id'], r2['source_record_id']])
                        candidates.add((id1, id2))
                        
        # Block D: exact amount + exact date
        bucket_d = {}
        for r in records:
            amt = r.get('amount_minor_units')
            date = r.get('transaction_date')
            if amt and date:
                bucket_d.setdefault((amt, date), []).append(r)
                
        for (amt, date), recs in bucket_d.items():
            for i in range(len(recs)):
                for j in range(i + 1, len(recs)):
                    r1 = recs[i]
                    r2 = recs[j]
                    if (r1.get('source'), r2.get('source')) in valid_pairs:
                        id1, id2 = sorted([r1['source_record_id'], r2['source_record_id']])
                        candidates.add((id1, id2))
                        
        candidate_count = len(candidates)
        reduction_factor = float('inf') if candidate_count == 0 else naive_comparison_count / candidate_count
        
        logger.info(f"Naive comparisons: {naive_comparison_count}, Candidates: {candidate_count}, Reduction factor: {reduction_factor:.2f}")
        
        return list(candidates)
