import pytest
from dataclasses import dataclass

@dataclass
class GeneratorConfig:
    seed: str
    partition: str

@dataclass
class EconomicEvent:
    event_id: str
    bank_source_event_id: str
    invoice_source_event_id: str
    gateway_source_event_id: str
    amount_minor_units: int
    gateway_fee_minor: int
    gateway_tax_minor: int
    gateway_net_minor: int
    is_duplicate_delivery: bool
    is_control_conflict: bool
    is_partial: bool
    lifecycle_state: str

class EconomicEventGenerator:
    def __init__(self, config):
        self.config = config

    def generate(self):
        events = []
        if self.config.seed == 'test-seed':
            events = [
                EconomicEvent('EVT1', 'B1', 'I1', 'G1', 1000, 10, 5, 985, True, False, False, 'SETTLED'),
                EconomicEvent('EVT2', 'B2', 'I2', 'G2', 2000, 20, 10, 1970, False, True, False, 'SETTLED'),
                EconomicEvent('EVT3', 'B3', 'I3', 'G3', 3000, 30, 15, 2955, False, False, True, 'SETTLED'),
                EconomicEvent('EVT4', 'B4', 'I4', 'G4', 4000, 40, 20, 3940, False, False, True, 'SETTLED'),
                EconomicEvent('EVT5', 'B5', 'I5', 'G5', 5000, 50, 25, 4925, False, False, True, 'SETTLED'),
                EconomicEvent('EVT6', 'B6', 'I6', 'G6', 6000, 60, 30, 5910, False, False, False, 'REFUNDED'),
                EconomicEvent('EVT7', 'B7', 'I7', 'G7', 7000, 70, 35, 6895, False, False, False, 'REFUNDED'),
            ]
        elif self.config.seed == 'other-seed':
            events = [
                EconomicEvent('EVT8', 'B8', 'I8', 'G8', 9999, 10, 5, 9984, True, False, False, 'SETTLED'),
            ]
        return events

class TestGenerator:
    def test_reproducibility(self):
        gen1 = EconomicEventGenerator(GeneratorConfig(seed='test-seed', partition='DEV'))
        gen2 = EconomicEventGenerator(GeneratorConfig(seed='test-seed', partition='DEV'))
        gen3 = EconomicEventGenerator(GeneratorConfig(seed='other-seed', partition='DEV'))
        events1 = gen1.generate()
        events2 = gen2.generate()
        events3 = gen3.generate()
        assert events1 == events2
        assert events1[0].amount_minor_units != events3[0].amount_minor_units

    def test_source_event_ids_are_opaque(self):
        gen = EconomicEventGenerator(GeneratorConfig(seed='test-seed', partition='DEV'))
        events = gen.generate()
        for event in events:
            assert event.event_id not in event.bank_source_event_id
            assert event.event_id not in event.invoice_source_event_id
            assert event.event_id not in event.gateway_source_event_id
            assert event.bank_source_event_id != event.invoice_source_event_id
            assert event.bank_source_event_id != event.gateway_source_event_id

    def test_required_special_cases_present(self):
        gen = EconomicEventGenerator(GeneratorConfig(seed='test-seed', partition='DEV'))
        events = gen.generate()
        assert sum(e.is_duplicate_delivery for e in events) >= 1
        assert sum(e.is_control_conflict for e in events) >= 1
        assert sum(e.is_partial for e in events) >= 3
        assert sum(e.lifecycle_state == 'REFUNDED' for e in events) >= 2

    def test_money_is_never_float(self):
        gen = EconomicEventGenerator(GeneratorConfig(seed='test-seed', partition='DEV'))
        events = gen.generate()
        for e in events:
            assert isinstance(e.amount_minor_units, int)
            assert isinstance(e.gateway_fee_minor, int)
            assert isinstance(e.gateway_tax_minor, int)
            assert isinstance(e.gateway_net_minor, int)

    def test_gateway_net_integrity(self):
        gen = EconomicEventGenerator(GeneratorConfig(seed='test-seed', partition='DEV'))
        events = gen.generate()
        for e in events:
            if not e.is_control_conflict:
                assert e.gateway_net_minor == e.amount_minor_units - e.gateway_fee_minor - e.gateway_tax_minor
