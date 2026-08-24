import pytest
from app.matching.allocator import OneToNAllocator, ComponentRejection

def test_transitive_graph_trap():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    gateway = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    
    # B-G = 0.91, G-I = 0.90, B-I = 0.42 (weak edge)
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.91},
                      {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.42}]),
        'G1': (gateway, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.91},
                         {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.90}]),
        'I1': (invoice, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.90},
                         {'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.42}])
    }
    
    # Should not produce a valid component because of the transitive trap B-I = 0.42 < 0.50
    valid_comps = allocator.group_and_validate(scored_records)
    assert len(valid_comps) == 0

def test_valid_3way_match():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    gateway = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    
    # All edges >= 0.80 except maybe B-I which is >= 0.50
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.95},
                      {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.85}]),
        'G1': (gateway, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95},
                         {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.95}]),
        'I1': (invoice, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.95},
                         {'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.85}])
    }
    
    valid_comps = allocator.group_and_validate(scored_records)
    assert len(valid_comps) == 1
    assert len(valid_comps[0]) == 3

def test_mixed_currency_fails():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'USD', 'amount_minor_units': 1000}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.95}]),
        'I1': (invoice, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95}])
    }
    
    assert len(allocator.group_and_validate(scored_records)) == 0

def test_amount_conservation_fails():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    inv1 = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 500}
    inv2 = {'source_record_id': 'I2', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 600} # Total 1100
    
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'I1', 'candidate_record': inv1, 'confidence_score': 0.95},
                      {'candidate_source_record_id': 'I2', 'candidate_record': inv2, 'confidence_score': 0.95}]),
        'I1': (inv1, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95}]),
        'I2': (inv2, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95}])
    }
    
    assert len(allocator.group_and_validate(scored_records)) == 0

def test_duplicate_entity_fails():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    # Two identical records (same sid)
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95}])
    }
    
    assert len(allocator.group_and_validate(scored_records)) == 0

def test_1_bank_1_gateway():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    gateway = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.95}]),
        'G1': (gateway, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95}])
    }
    valid_comps = allocator.group_and_validate(scored_records)
    assert len(valid_comps) == 1
    assert len(valid_comps[0]) == 2

def test_1_bank_1_invoice():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.95}]),
        'I1': (invoice, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95}])
    }
    valid_comps = allocator.group_and_validate(scored_records)
    assert len(valid_comps) == 1
    assert len(valid_comps[0]) == 2

def test_1_bank_N_invoices():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1500}
    inv1 = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 500}
    inv2 = {'source_record_id': 'I2', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'I1', 'candidate_record': inv1, 'confidence_score': 0.95},
                      {'candidate_source_record_id': 'I2', 'candidate_record': inv2, 'confidence_score': 0.95}]),
        'I1': (inv1, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95}]),
        'I2': (inv2, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95}])
    }
    valid_comps = allocator.group_and_validate(scored_records)
    assert len(valid_comps) == 1
    assert len(valid_comps[0]) == 3

def test_N_banks_1_invoice():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank1 = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 500}
    bank2 = {'source_record_id': 'B2', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 500}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    scored_records = {
        'I1': (invoice, [{'candidate_source_record_id': 'B1', 'candidate_record': bank1, 'confidence_score': 0.95},
                         {'candidate_source_record_id': 'B2', 'candidate_record': bank2, 'confidence_score': 0.95}]),
        'B1': (bank1, [{'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.95}]),
        'B2': (bank2, [{'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.95}])
    }
    valid_comps = allocator.group_and_validate(scored_records)
    assert len(valid_comps) == 1
    assert len(valid_comps[0]) == 3

def test_candidate_in_multiple_components():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank1 = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    bank2 = {'source_record_id': 'B2', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    inv = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    # Bank1 and Bank2 both claim I1.
    scored_records = {
        'I1': (inv, [{'candidate_source_record_id': 'B1', 'candidate_record': bank1, 'confidence_score': 0.95},
                     {'candidate_source_record_id': 'B2', 'candidate_record': bank2, 'confidence_score': 0.95}]),
        'B1': (bank1, [{'candidate_source_record_id': 'I1', 'candidate_record': inv, 'confidence_score': 0.95}]),
        'B2': (bank2, [{'candidate_source_record_id': 'I1', 'candidate_record': inv, 'confidence_score': 0.95}])
    }
    # This forms a single component (B1-I1-B2). 
    # But this is an invalid cardinality (2 Banks, 1 Invoice with amounts 1000, 1000, 1000). Amount conservation fails!
    # B1+B2 = 2000 != 1000. So it should be rejected.
    assert len(allocator.group_and_validate(scored_records)) == 0

if __name__ == '__main__':
    pytest.main([__file__])
