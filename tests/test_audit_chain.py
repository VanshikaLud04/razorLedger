import pytest
from app.audit_chain import HashChainVerifier, canonical_json

def make_entry(entity_id, decision_id, timestamp, action, reason, metadata, previous_hash):
    current_hash = HashChainVerifier.generate_hash(
        entity_id=entity_id,
        decision_id=decision_id,
        timestamp=timestamp,
        action=action,
        reason=reason,
        metadata=metadata,
        previous_hash=previous_hash
    )
    return {
        "entity_id": entity_id,
        "decision_id": decision_id,
        "timestamp": timestamp,
        "action": action,
        "reason": reason,
        "metadata": metadata,
        "previous_hash": previous_hash,
        "current_hash": current_hash
    }

def test_newly_created_chain_verifies():
    entries = [
        make_entry("e1", "d1", "2023-01-01T00:00:00Z", "CREATE", "init", {}, "GENESIS")
    ]
    verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
    assert verified is True
    assert broken_idx is None

def test_multiple_sequential_entries_verify():
    e1 = make_entry("e1", "d1", "2023-01-01T00:00:00Z", "CREATE", "init", {}, "GENESIS")
    e2 = make_entry("e1", "d2", "2023-01-01T00:01:00Z", "UPDATE", "change", {}, e1['current_hash'])
    e3 = make_entry("e1", "d3", "2023-01-01T00:02:00Z", "REVIEW", "review", {}, e2['current_hash'])
    
    entries = [e1, e2, e3]
    verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
    assert verified is True

def test_modifying_audit_entry_fails():
    e1 = make_entry("e1", "d1", "2023-01-01T00:00:00Z", "CREATE", "init", {}, "GENESIS")
    e2 = make_entry("e1", "d2", "2023-01-01T00:01:00Z", "UPDATE", "change", {}, e1['current_hash'])
    
    # Tamper with action
    e2['action'] = "TAMPERED"
    
    entries = [e1, e2]
    verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
    assert verified is False
    assert broken_idx == 1
    assert failure_reason == "CURRENT_HASH_MISMATCH"

def test_modifying_previous_hash_fails():
    e1 = make_entry("e1", "d1", "2023-01-01T00:00:00Z", "CREATE", "init", {}, "GENESIS")
    e2 = make_entry("e1", "d2", "2023-01-01T00:01:00Z", "UPDATE", "change", {}, e1['current_hash'])
    
    # Tamper with previous_hash link
    e2['previous_hash'] = "fakehash"
    
    entries = [e1, e2]
    verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
    assert verified is False
    assert broken_idx == 1
    assert failure_reason == "PREVIOUS_HASH_MISMATCH"

def test_modifying_current_hash_fails():
    e1 = make_entry("e1", "d1", "2023-01-01T00:00:00Z", "CREATE", "init", {}, "GENESIS")
    
    e1['current_hash'] = "tamperedhash"
    
    entries = [e1]
    verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
    assert verified is False
    assert broken_idx == 0
    assert failure_reason == "CURRENT_HASH_MISMATCH"

def test_reordering_fails():
    e1 = make_entry("e1", "d1", "2023-01-01T00:00:00Z", "CREATE", "init", {}, "GENESIS")
    e2 = make_entry("e1", "d2", "2023-01-01T00:01:00Z", "UPDATE", "change", {}, e1['current_hash'])
    
    # Reorder
    entries = [e2, e1]
    verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
    assert verified is False
    assert broken_idx == 0
    assert failure_reason == "GENESIS_MISMATCH"

def test_deleting_intermediate_fails():
    e1 = make_entry("e1", "d1", "2023-01-01T00:00:00Z", "CREATE", "init", {}, "GENESIS")
    e2 = make_entry("e1", "d2", "2023-01-01T00:01:00Z", "UPDATE", "change", {}, e1['current_hash'])
    e3 = make_entry("e1", "d3", "2023-01-01T00:02:00Z", "REVIEW", "review", {}, e2['current_hash'])
    
    # Delete e2
    entries = [e1, e3]
    verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
    assert verified is False
    assert broken_idx == 1
    assert failure_reason == "PREVIOUS_HASH_MISMATCH"

def test_canonical_json_is_deterministic():
    d1 = {"a": 1, "b": 2, "c": 3}
    d2 = {"c": 3, "a": 1, "b": 2}
    
    assert canonical_json(d1) == canonical_json(d2)

def test_genesis_mismatch():
    e1 = make_entry("e1", "d1", "2023-01-01T00:00:00Z", "CREATE", "init", {}, "NOT_GENESIS")
    
    entries = [e1]
    verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
    assert verified is False
    assert broken_idx == 0
    assert failure_reason == "GENESIS_MISMATCH"

def test_empty_chain_is_verified():
    verified, broken_idx, failure_reason = HashChainVerifier.verify_chain([])
    assert verified is True
