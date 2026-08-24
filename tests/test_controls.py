"""
tests/test_controls.py — Tests the REAL FinancialControlEngine.
Each test exercises the actual check_ method with a bad context (FAIL)
and a good context (PASS). No mock logic — this tests the real code.
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.controls.engine import FinancialControlEngine

CONFIG = {
    'allocation': {'fee_adjustment_tolerance_minor': 100},
    'matching': {'settlement_window_days': 5},
}

engine = FinancialControlEngine(CONFIG)


class TestControls:
    def test_ctrl001_no_double_allocation(self):
        bad = {
            'proposed_allocation_lines': [{'source_record_id': 'R1'}],
            'existing_allocated_ids': {'R1'},
        }
        good = {
            'proposed_allocation_lines': [{'source_record_id': 'R2'}],
            'existing_allocated_ids': {'R1'},
        }
        assert engine.check_ctrl001_no_double_allocation(bad).status == 'FAIL'
        assert engine.check_ctrl001_no_double_allocation(good).status == 'PASS'

    def test_ctrl002_currency_mismatch(self):
        bad  = {'currencies': ['INR', 'USD']}
        good = {'currencies': ['INR', 'INR']}
        assert engine.check_ctrl002_currency_consistency(bad).status == 'FAIL'
        assert engine.check_ctrl002_currency_consistency(good).status == 'PASS'

    def test_ctrl003_settlement_conservation_failure(self):
        # gross=10000, fee=230, tax=41, bank_credit=9000 → mismatch > 100
        bad = {
            'gateway_gross_minor': 10000,
            'gateway_fee_minor': 230,
            'gateway_tax_minor': 41,
            'bank_credit_minor': 9000,
        }
        # bank_credit = 10000 - 230 - 41 = 9729 → within tolerance
        good = {
            'gateway_gross_minor': 10000,
            'gateway_fee_minor': 230,
            'gateway_tax_minor': 41,
            'bank_credit_minor': 9729,
        }
        assert engine.check_ctrl003_settlement_conservation(bad).status == 'FAIL'
        assert engine.check_ctrl003_settlement_conservation(good).status == 'PASS'

    def test_ctrl004_gross_fee_tax_net_inconsistency(self):
        # This is the deliberate generator conflict case (gateway net wrong by 500)
        bad = {
            'gateway_gross_minor': 10000,
            'gateway_fee_minor': 230,
            'gateway_tax_minor': 41,
            'gateway_net_minor': 10229,  # wrong: should be 9729
        }
        good = {
            'gateway_gross_minor': 10000,
            'gateway_fee_minor': 230,
            'gateway_tax_minor': 41,
            'gateway_net_minor': 9729,   # correct: 10000 - 230 - 41
        }
        assert engine.check_ctrl004_gross_fee_tax_net_consistency(bad).status == 'FAIL'
        assert engine.check_ctrl004_gross_fee_tax_net_consistency(good).status == 'PASS'

    def test_ctrl005_negative_outstanding_balance(self):
        bad  = {'invoice_amount_minor': 10000, 'total_allocated_minor': 10500}
        good = {'invoice_amount_minor': 10000, 'total_allocated_minor': 10000}
        assert engine.check_ctrl005_no_negative_outstanding(bad).status == 'FAIL'
        assert engine.check_ctrl005_no_negative_outstanding(good).status == 'PASS'

    def test_ctrl006_refund_exceeds_captured(self):
        bad  = {'refund_amount_minor': 5000, 'captured_amount_minor': 4000}
        good = {'refund_amount_minor': 3000, 'captured_amount_minor': 4000}
        assert engine.check_ctrl006_refund_lte_captured(bad).status == 'FAIL'
        assert engine.check_ctrl006_refund_lte_captured(good).status == 'PASS'

    def test_ctrl007_invalid_lifecycle_transition(self):
        bad  = {'from_state': 'SETTLED', 'to_state': 'INITIATED'}   # SETTLED→INITIATED invalid
        good = {'from_state': 'CAPTURED', 'to_state': 'SETTLED'}    # CAPTURED→SETTLED valid
        assert engine.check_ctrl007_lifecycle_transition_validity(bad).status == 'FAIL'
        assert engine.check_ctrl007_lifecycle_transition_validity(good).status == 'PASS'

    def test_ctrl008_missing_disposition(self):
        bad  = {'total_source_records': 10, 'total_decisions': 9}
        good = {'total_source_records': 10, 'total_decisions': 10}
        assert engine.check_ctrl008_every_source_record_has_disposition(bad).status == 'FAIL'
        assert engine.check_ctrl008_every_source_record_has_disposition(good).status == 'PASS'

    def test_ctrl009_duplicate_event_allocation(self):
        bad  = {
            'deduplicated_source_event_ids': {'EVT-001'},
            'proposed_source_record_ids': {'EVT-001'},
        }
        good = {
            'deduplicated_source_event_ids': {'EVT-001'},
            'proposed_source_record_ids': {'EVT-002'},
        }
        assert engine.check_ctrl009_no_duplicate_event_creates_new_allocation(bad).status == 'FAIL'
        assert engine.check_ctrl009_no_duplicate_event_creates_new_allocation(good).status == 'PASS'

    def test_ctrl010_source_semantics_violation(self):
        # BANK matched to INVOICE without gateway context → FAIL
        bad  = {'source_a': 'BANK', 'source_b': 'INVOICE'}
        # BANK matched to GATEWAY with gateway context → PASS
        good = {'source_a': 'BANK', 'source_b': 'GATEWAY',
                'gateway_gross_minor': 10000}
        assert engine.check_ctrl010_source_semantics_respected(bad).status == 'FAIL'
        assert engine.check_ctrl010_source_semantics_respected(good).status == 'PASS'

    def test_verifier_rejects_high_confidence_match_on_control_failure(self):
        """
        The hostile-judge case from 04-ROADMAP.md:
        matcher confidence high → CTRL-001 fires → final decision MUST be REVIEW not MATCH.
        This test verifies the control engine produces the FAIL that forces REVIEW.
        The decision engine test (test_matching.py) verifies it routes to REVIEW.
        """
        # Simulate: same record proposed for allocation twice
        ctx = {
            'proposed_allocation_lines': [{'source_record_id': 'ALREADY-ALLOCATED'}],
            'existing_allocated_ids': {'ALREADY-ALLOCATED'},
        }
        result = engine.check_ctrl001_no_double_allocation(ctx)
        assert result.status == 'FAIL'
    def test_ctrl005_under_allocation_passes(self):
        # Under allocation is fine (e.g. partial payment)
        ctx = {'invoice_amount_minor': 10000, 'total_allocated_minor': 5000}
        assert engine.check_ctrl005_no_negative_outstanding(ctx).status == 'PASS'

    def test_ctrl003_exact_conservation_no_fees(self):
        # Exact conservation without any fees
        bad = {
            'gateway_gross_minor': 10000,
            'gateway_fee_minor': 0,
            'gateway_tax_minor': 0,
            'bank_credit_minor': 9000,
        }
        good = {
            'gateway_gross_minor': 10000,
            'gateway_fee_minor': 0,
            'gateway_tax_minor': 0,
            'bank_credit_minor': 10000,
        }
        assert engine.check_ctrl003_settlement_conservation(bad).status == 'FAIL'
        assert engine.check_ctrl003_settlement_conservation(good).status == 'PASS'

