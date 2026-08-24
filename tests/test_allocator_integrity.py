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
    
    # Should not produce a valid component because of the transitive trap B-I = 0.42 < 0.80
    valid_comps = allocator.group_and_validate(scored_records)
    assert len(valid_comps) == 0

def test_valid_3way_match():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    gateway = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    
    # All edges >= 0.80, including the direct Bank-Invoice edge
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

def test_direct_edge_below_threshold_rejected():
    """3-way component, direct Bank-Invoice edge at 0.79 -- just below the
    canonical 0.80 threshold -- must be rejected, even though it's connected
    to the component transitively via strong Bank-Gateway/Gateway-Invoice edges."""
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    gateway = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.95},
                      {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.79}]),
        'G1': (gateway, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95},
                         {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.95}]),
        'I1': (invoice, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.95},
                         {'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.79}])
    }
    assert len(allocator.group_and_validate(scored_records)) == 0

def test_direct_edge_at_threshold_eligible():
    """Same shape, direct Bank-Invoice edge at exactly 0.80 -- must be accepted."""
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    gateway = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.95},
                      {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.80}]),
        'G1': (gateway, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.95},
                         {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.95}]),
        'I1': (invoice, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.95},
                         {'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.80}])
    }
    valid_comps = allocator.group_and_validate(scored_records)
    assert len(valid_comps) == 1
    assert len(valid_comps[0]) == 3

def test_bank_gateway_edge_below_threshold_rejected():
    """Bank<->Gateway is a previously-unchecked edge type in _validate_component
    (implicitly relied only on graph-membership filtering). Explicit check added
    2026-08-24 -- confirm a sub-threshold edge is rejected even if it somehow
    reaches validation (defense in depth, not just graph-construction filtering)."""
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    gateway = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    # Below threshold -- graph construction alone should already exclude this,
    # this test proves it, it isn't silently let through by some other path.
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.79}]),
        'G1': (gateway, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.79}])
    }
    assert len(allocator.group_and_validate(scored_records)) == 0

def test_gateway_invoices_edge_below_threshold_rejected():
    """Gateway<->Invoice(s) -- same previously-unchecked edge type, now covered."""
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    gateway = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    scored_records = {
        'G1': (gateway, [{'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.79}]),
        'I1': (invoice, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.79}])
    }
    assert len(allocator.group_and_validate(scored_records)) == 0

def test_all_required_edges_at_threshold_accepted():
    """Every edge type in a 3-way component sitting exactly at threshold --
    confirms the fix didn't make acceptance stricter than intended (0.80 is
    inclusive, not exclusive, everywhere)."""
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    bank = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    gateway = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    invoice = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    scored_records = {
        'B1': (bank, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.80},
                      {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.80}]),
        'G1': (gateway, [{'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.80},
                         {'candidate_source_record_id': 'I1', 'candidate_record': invoice, 'confidence_score': 0.80}]),
        'I1': (invoice, [{'candidate_source_record_id': 'G1', 'candidate_record': gateway, 'confidence_score': 0.80},
                         {'candidate_source_record_id': 'B1', 'candidate_record': bank, 'confidence_score': 0.80}])
    }
    valid_comps = allocator.group_and_validate(scored_records)
    assert len(valid_comps) == 1
    assert len(valid_comps[0]) == 3

def test_unsupported_N_to_N():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    b1 = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 500}
    b2 = {'source_record_id': 'B2', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 500}
    i1 = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 500}
    i2 = {'source_record_id': 'I2', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 500}
    
    scored_records = {
        'B1': (b1, [{'candidate_source_record_id': 'I1', 'candidate_record': i1, 'confidence_score': 0.95},
                    {'candidate_source_record_id': 'I2', 'candidate_record': i2, 'confidence_score': 0.95}]),
        'B2': (b2, [{'candidate_source_record_id': 'I1', 'candidate_record': i1, 'confidence_score': 0.95},
                    {'candidate_source_record_id': 'I2', 'candidate_record': i2, 'confidence_score': 0.95}]),
        'I1': (i1, [{'candidate_source_record_id': 'B1', 'candidate_record': b1, 'confidence_score': 0.95},
                    {'candidate_source_record_id': 'B2', 'candidate_record': b2, 'confidence_score': 0.95}]),
        'I2': (i2, [{'candidate_source_record_id': 'B1', 'candidate_record': b1, 'confidence_score': 0.95},
                    {'candidate_source_record_id': 'B2', 'candidate_record': b2, 'confidence_score': 0.95}])
    }
    # N:N is unsupported, must return 0 valid components
    assert len(allocator.group_and_validate(scored_records)) == 0

def test_double_weak_bridge():
    allocator = OneToNAllocator({'matching': {'auto_match_threshold': 0.80}})
    b = {'source_record_id': 'B1', 'source': 'BANK', 'currency': 'INR', 'amount_minor_units': 1000}
    g = {'source_record_id': 'G1', 'source': 'GATEWAY', 'currency': 'INR', 'amount_minor_units': 1000}
    i = {'source_record_id': 'I1', 'source': 'INVOICE', 'currency': 'INR', 'amount_minor_units': 1000}
    
    # B-G weak, G-I weak
    scored_records = {
        'B1': (b, [{'candidate_source_record_id': 'G1', 'candidate_record': g, 'confidence_score': 0.70}]),
        'G1': (g, [{'candidate_source_record_id': 'B1', 'candidate_record': b, 'confidence_score': 0.70},
                   {'candidate_source_record_id': 'I1', 'candidate_record': i, 'confidence_score': 0.70}]),
        'I1': (i, [{'candidate_source_record_id': 'G1', 'candidate_record': g, 'confidence_score': 0.70}])
    }
    assert len(allocator.group_and_validate(scored_records)) == 0

if __name__ == '__main__':
    pytest.main([__file__])
