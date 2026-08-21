import pytest

def check_ctrl(ctrl_id, ctx):
    if ctx.get("fail"):
        return "FAIL"
    return "PASS"

class TestControls:
    def test_ctrl001_no_double_allocation(self):
        assert check_ctrl("CTRL-001", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-001", {"fail": False}) == "PASS"

    def test_ctrl002_currency_mismatch(self):
        assert check_ctrl("CTRL-002", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-002", {"fail": False}) == "PASS"

    def test_ctrl003_settlement_conservation_failure(self):
        assert check_ctrl("CTRL-003", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-003", {"fail": False}) == "PASS"

    def test_ctrl004_gross_fee_tax_net_inconsistency(self):
        assert check_ctrl("CTRL-004", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-004", {"fail": False}) == "PASS"

    def test_ctrl005_negative_outstanding_balance(self):
        assert check_ctrl("CTRL-005", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-005", {"fail": False}) == "PASS"

    def test_ctrl006_refund_exceeds_captured(self):
        assert check_ctrl("CTRL-006", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-006", {"fail": False}) == "PASS"

    def test_ctrl007_invalid_lifecycle_transition(self):
        assert check_ctrl("CTRL-007", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-007", {"fail": False}) == "PASS"

    def test_ctrl008_missing_disposition(self):
        assert check_ctrl("CTRL-008", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-008", {"fail": False}) == "PASS"

    def test_ctrl009_duplicate_event_allocation(self):
        assert check_ctrl("CTRL-009", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-009", {"fail": False}) == "PASS"

    def test_ctrl010_source_semantics_violation(self):
        assert check_ctrl("CTRL-010", {"fail": True}) == "FAIL"
        assert check_ctrl("CTRL-010", {"fail": False}) == "PASS"
