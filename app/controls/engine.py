from dataclasses import dataclass

@dataclass
class ControlCheckResult:
    control_id: str
    status: str
    message: str
    related_entity_ids: list[str]

class FinancialControlEngine:
    VALID_TRANSITIONS = {
        'INITIATED': {'CAPTURED'},
        'CAPTURED': {'PARTIALLY_SETTLED', 'SETTLED', 'REFUNDED', 'FAILED'},
        'PARTIALLY_SETTLED': {'SETTLED', 'REFUNDED'},
        'SETTLED': {'REFUNDED', 'REVERSED'},
        'REFUNDED': set(),
        'REVERSED': set(),
        'FAILED': set(),
    }

    def __init__(self, config: dict):
        self.config = config
        self.fee_adjustment_tolerance = config.get('allocation', {}).get('fee_adjustment_tolerance_minor', 100)

    def run_all(self, context: dict) -> list[ControlCheckResult]:
        results = [
            self.check_ctrl001_no_double_allocation(context),
            self.check_ctrl002_currency_consistency(context),
            self.check_ctrl003_settlement_conservation(context),
            self.check_ctrl004_gross_fee_tax_net_consistency(context),
            self.check_ctrl005_no_negative_outstanding(context),
            self.check_ctrl006_refund_lte_captured(context),
            self.check_ctrl007_lifecycle_transition_validity(context),
            self.check_ctrl008_every_source_record_has_disposition(context),
            self.check_ctrl009_no_duplicate_event_creates_new_allocation(context),
            self.check_ctrl010_source_semantics_respected(context),
        ]
        return results

    def check_ctrl001_no_double_allocation(self, context: dict) -> ControlCheckResult:
        proposed = context.get('proposed_allocation_lines', [])
        existing = context.get('existing_allocated_ids', set())
        
        proposed_ids = [line['source_record_id'] for line in proposed]
        duplicates = [pid for pid in proposed_ids if pid in existing]
        
        if duplicates:
            return ControlCheckResult('CTRL-001', 'FAIL', 'Double allocation detected', duplicates)
        
        # Check internal duplicates in proposal
        if len(proposed_ids) != len(set(proposed_ids)):
            return ControlCheckResult('CTRL-001', 'FAIL', 'Duplicate source_record_id in proposal', list(set(proposed_ids)))

        return ControlCheckResult('CTRL-001', 'PASS', 'No double allocation', proposed_ids)

    def check_ctrl002_currency_consistency(self, context: dict) -> ControlCheckResult:
        currencies = context.get('currencies', [])
        if not currencies:
            return ControlCheckResult('CTRL-002', 'PASS', 'No currencies to check', [])
            
        unique_currencies = set(currencies)
        if len(unique_currencies) > 1:
            return ControlCheckResult('CTRL-002', 'FAIL', f'Mixed currencies: {unique_currencies}', [])
            
        return ControlCheckResult('CTRL-002', 'PASS', 'Currencies consistent', [])

    def check_ctrl003_settlement_conservation(self, context: dict) -> ControlCheckResult:
        if 'gateway_gross_minor' not in context or 'bank_credit_minor' not in context:
            return ControlCheckResult('CTRL-003', 'PASS', 'Not applicable', [])
            
        gross = context.get('gateway_gross_minor', 0)
        fee = context.get('gateway_fee_minor', 0)
        tax = context.get('gateway_tax_minor', 0)
        bank_credit = context.get('bank_credit_minor', 0)
        adj = context.get('adjustment_minor', 0)
        
        expected = gross - fee - tax + adj
        if abs(expected - bank_credit) > self.fee_adjustment_tolerance:
            return ControlCheckResult('CTRL-003', 'FAIL', f'Settlement mismatch: expected {expected}, got {bank_credit}', [])
            
        return ControlCheckResult('CTRL-003', 'PASS', 'Settlement conserved', [])

    def check_ctrl004_gross_fee_tax_net_consistency(self, context: dict) -> ControlCheckResult:
        if 'gateway_net_minor' not in context:
            return ControlCheckResult('CTRL-004', 'PASS', 'Not applicable', [])
            
        gross = context.get('gateway_gross_minor', 0)
        fee = context.get('gateway_fee_minor', 0)
        tax = context.get('gateway_tax_minor', 0)
        net = context.get('gateway_net_minor', 0)
        
        if abs(gross - fee - tax - net) > 1:
            return ControlCheckResult('CTRL-004', 'FAIL', f'Net mismatch: expected {gross - fee - tax}, got {net}', [])
            
        return ControlCheckResult('CTRL-004', 'PASS', 'Gross/fee/tax/net consistent', [])

    def check_ctrl005_no_negative_outstanding(self, context: dict) -> ControlCheckResult:
        if 'invoice_amount_minor' not in context:
            return ControlCheckResult('CTRL-005', 'PASS', 'Not applicable', [])
            
        invoice = context.get('invoice_amount_minor', 0)
        allocated = context.get('total_allocated_minor', 0)
        
        if invoice - allocated < 0:
            return ControlCheckResult('CTRL-005', 'FAIL', 'Negative outstanding balance', [])
            
        return ControlCheckResult('CTRL-005', 'PASS', 'Balance >= 0', [])

    def check_ctrl006_refund_lte_captured(self, context: dict) -> ControlCheckResult:
        if 'refund_amount_minor' not in context:
            return ControlCheckResult('CTRL-006', 'PASS', 'Not applicable', [])
            
        refund = context.get('refund_amount_minor', 0)
        captured = context.get('captured_amount_minor', 0)
        
        if refund > captured:
            return ControlCheckResult('CTRL-006', 'FAIL', 'Refund exceeds captured amount', [])
            
        return ControlCheckResult('CTRL-006', 'PASS', 'Refund <= captured', [])

    def check_ctrl007_lifecycle_transition_validity(self, context: dict) -> ControlCheckResult:
        if 'from_state' not in context or 'to_state' not in context:
            return ControlCheckResult('CTRL-007', 'PASS', 'Not applicable', [])
            
        from_state = context.get('from_state')
        to_state = context.get('to_state')
        
        valid_next = self.VALID_TRANSITIONS.get(from_state, set())
        if to_state not in valid_next:
            return ControlCheckResult('CTRL-007', 'FAIL', f'Invalid transition: {from_state} -> {to_state}', [])
            
        return ControlCheckResult('CTRL-007', 'PASS', 'Valid transition', [])

    def check_ctrl008_every_source_record_has_disposition(self, context: dict) -> ControlCheckResult:
        if 'total_source_records' not in context:
            return ControlCheckResult('CTRL-008', 'PASS', 'Not applicable', [])
            
        records = context.get('total_source_records', 0)
        decisions = context.get('total_decisions', 0)
        
        if records != decisions:
            return ControlCheckResult('CTRL-008', 'FAIL', f'Mismatch: {records} records, {decisions} decisions', [])
            
        return ControlCheckResult('CTRL-008', 'PASS', 'All records have disposition', [])

    def check_ctrl009_no_duplicate_event_creates_new_allocation(self, context: dict) -> ControlCheckResult:
        deduped = context.get('deduplicated_source_event_ids', set())
        proposed = context.get('proposed_source_record_ids', set())
        
        overlap = deduped.intersection(proposed)
        if overlap:
            return ControlCheckResult('CTRL-009', 'FAIL', 'Proposed allocation uses deduplicated events', list(overlap))
            
        return ControlCheckResult('CTRL-009', 'PASS', 'No duplicate events used', [])

    def check_ctrl010_source_semantics_respected(self, context: dict) -> ControlCheckResult:
        source_a = context.get('source_a')
        source_b = context.get('source_b')
        
        if source_a == 'BANK' and source_b == 'INVOICE':
            # Bank to Invoice direct match might bypass Gateway net check
            if 'gateway_gross_minor' not in context:
                return ControlCheckResult('CTRL-010', 'FAIL', 'Bank matched to Invoice without Gateway', [])
                
        return ControlCheckResult('CTRL-010', 'PASS', 'Semantics respected', [])
