import hashlib
import json
from typing import Dict, Any, List, Tuple, Optional

def canonical_json(data: Dict[str, Any]) -> str:
    """
    Produce a deterministic JSON string representation.
    Keys are sorted, and separators are minimized to eliminate whitespace variations.
    """
    return json.dumps(data, sort_keys=True, separators=(',', ':'))

class HashChainVerifier:
    @staticmethod
    def generate_hash(
        entity_id: str,
        decision_id: str,
        timestamp: str,
        action: str,
        reason: str,
        metadata: Dict[str, Any],
        previous_hash: str
    ) -> str:
        data = {
            "entity_id": str(entity_id) if entity_id else "",
            "decision_id": str(decision_id) if decision_id else "",
            "timestamp": str(timestamp) if timestamp else "",
            "action": str(action) if action else "",
            "reason": str(reason) if reason else "",
            "metadata": metadata if metadata is not None else {},
            "previous_hash": str(previous_hash) if previous_hash else ""
        }
        canonical_str = canonical_json(data)
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_chain(entries: List[Dict[str, Any]]) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Verify an ordered list of audit entries.
        Each entry must be a dictionary containing fields needed for generate_hash plus 'current_hash'.
        Returns (is_verified, first_broken_index, failure_reason)
        """
        if not entries:
            return True, None, None
            
        computed_prev = "GENESIS"
        
        for idx, entry in enumerate(entries):
            prev_hash = entry.get('previous_hash')
            if prev_hash != computed_prev:
                if idx == 0 and prev_hash != "GENESIS":
                    return False, idx, "GENESIS_MISMATCH"
                return False, idx, "PREVIOUS_HASH_MISMATCH"
                
            expected_hash = HashChainVerifier.generate_hash(
                entity_id=entry.get('entity_id'),
                decision_id=entry.get('decision_id'),
                timestamp=entry.get('timestamp'),
                action=entry.get('action'),
                reason=entry.get('reason'),
                metadata=entry.get('metadata', {}),
                previous_hash=prev_hash
            )
            
            curr_hash = entry.get('current_hash')
            if curr_hash != expected_hash:
                return False, idx, "CURRENT_HASH_MISMATCH"
                
            computed_prev = curr_hash
            
        return True, None, None
