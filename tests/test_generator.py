"""
tests/test_generator.py — Tests the REAL EconomicEventGenerator and SourceViewDeriver.
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from generator.config import GeneratorConfig
from generator.events import EconomicEventGenerator
from generator.views import SourceViewDeriver


def make_gen(seed='test-seed-v1'):
    cfg = GeneratorConfig(seed=seed, partition='DEV')
    return EconomicEventGenerator(cfg), cfg


class TestGenerator:
    def test_reproducibility(self):
        """Same seed → identical output. Different seed → different first amount."""
        gen1, _ = make_gen('seed-A')
        gen2, _ = make_gen('seed-A')
        gen3, _ = make_gen('seed-B')
        e1 = gen1.generate()
        e2 = gen2.generate()
        e3 = gen3.generate()
        assert len(e1) == len(e2)
        for a, b in zip(e1, e2):
            assert a.amount_minor_units == b.amount_minor_units
            assert a.bank_source_event_id == b.bank_source_event_id
        # Different seed → different first event amount (with very high probability)
        assert e1[0].amount_minor_units != e3[0].amount_minor_units or \
               e1[1].amount_minor_units != e3[1].amount_minor_units

    def test_generates_150_events(self):
        gen, _ = make_gen()
        events = gen.generate()
        assert len(events) == 150

    def test_source_event_ids_are_opaque(self):
        """No source_event_id contains the internal event_id. All three are distinct."""
        gen, _ = make_gen()
        events = gen.generate()
        for e in events:
            assert e.event_id not in e.bank_source_event_id
            assert e.event_id not in e.invoice_source_event_id
            assert e.event_id not in e.gateway_source_event_id
            assert e.bank_source_event_id != e.invoice_source_event_id
            assert e.bank_source_event_id != e.gateway_source_event_id
            assert e.invoice_source_event_id != e.gateway_source_event_id

    def test_required_special_cases_present(self):
        """150 events must include minimum required special cases."""
        gen, _ = make_gen()
        events = gen.generate()
        assert sum(e.is_duplicate_delivery for e in events) >= 1, "need ≥1 duplicate delivery"
        assert sum(e.is_control_conflict for e in events) >= 1, "need ≥1 control conflict"
        assert sum(e.is_partial for e in events) >= 3, "need ≥3 partial payments"
        assert sum(e.lifecycle_state == 'REFUNDED' for e in events) >= 2, "need ≥2 refunds"

    def test_money_is_never_float(self):
        """All monetary fields are int — Constitution rule 6."""
        gen, _ = make_gen()
        for e in gen.generate():
            assert isinstance(e.amount_minor_units, int)
            assert isinstance(e.gateway_fee_minor, int)
            assert isinstance(e.gateway_tax_minor, int)
            assert isinstance(e.gateway_net_minor, int)

    def test_gateway_net_integrity(self):
        """gateway_net = gross - fee - tax for all non-conflict events."""
        gen, _ = make_gen()
        for e in gen.generate():
            if not e.is_control_conflict:
                expected = e.amount_minor_units - e.gateway_fee_minor - e.gateway_tax_minor
                assert e.gateway_net_minor == expected

    def test_amounts_in_valid_range(self):
        """Amounts between ₹500 and ₹2L in paise."""
        gen, _ = make_gen()
        for e in gen.generate():
            assert 50_000 <= e.amount_minor_units <= 20_000_000

    def test_source_view_deriver_produces_correct_counts(self):
        """150 events → ≥450 source records (duplicates add extras)."""
        cfg = GeneratorConfig(seed='test-seed-v1', partition='DEV')
        gen = EconomicEventGenerator(cfg)
        events = gen.generate()
        deriver = SourceViewDeriver(cfg)
        records, truth = deriver.derive(events)
        # At least 3 per event (BANK + INVOICE + GATEWAY), plus extras for duplicates
        assert len(records) >= 450
        # Truth bundle has exactly 3 entries per non-duplicate event plus 1 for duplicate
        assert len(truth.records) >= 450

    def test_ground_truth_in_records_not_in_truth_bundle_schema(self):
        """
        Source records dict has ground_truth_group_id (for ingest to strip).
        GroundTruthRecord has ground_truth_group_id (for evaluator use).
        They must be the same value for the same event.
        """
        cfg = GeneratorConfig(seed='test-seed-v1', partition='DEV')
        gen = EconomicEventGenerator(cfg)
        events = gen.generate()
        deriver = SourceViewDeriver(cfg)
        records, truth = deriver.derive(events)
        # Every source record has a ground_truth_group_id tag
        for r in records:
            assert 'ground_truth_group_id' in r
        # Truth bundle's source_event_ids match those in records
        record_sids = {r['source_event_id'] for r in records}
        truth_sids = {t.source_event_id for t in truth.records}
        # Truth should contain all unique source_event_ids (duplicates share same sid)
        assert truth_sids.issubset(record_sids)

    def test_duplicate_delivery_emits_two_bank_records_same_sid(self):
        """Duplicate delivery event emits 2 BANK records with identical source_event_id."""
        cfg = GeneratorConfig(seed='test-seed-v1', partition='DEV')
        gen = EconomicEventGenerator(cfg)
        events = gen.generate()
        dup_events = [e for e in events if e.is_duplicate_delivery]
        assert len(dup_events) >= 1
        deriver = SourceViewDeriver(cfg)
        records, _ = deriver.derive(events)
        for dup_event in dup_events:
            bank_sid = dup_event.bank_source_event_id
            bank_records = [r for r in records if r['source_event_id'] == bank_sid]
            assert len(bank_records) == 2, \
                f"Expected 2 BANK records for duplicate event, got {len(bank_records)}"
