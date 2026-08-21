"""
generator/events.py — Economic event generator.

Generates 150 EconomicEvent records with realistic Indian merchant data.
All generation is deterministic: same seed → same output, every run.

BENCHMARK INTEGRITY RULES (non-negotiable):
  - ground_truth_group_id  → evaluator only (generator/truth.py)
  - event_id               → internal generator only; NEVER reaches matcher
  - source_event_ids       → opaque, per-source, unguessable from each other
                             (generated via UUID4 seeded from partition seed)

The matcher cannot reconstruct the economic_event_id from any source_event_id.
"""

import hashlib
import uuid
import random
from datetime import date, timedelta
from dataclasses import dataclass, field
from faker import Faker

from .config import GeneratorConfig


@dataclass
class EconomicEvent:
    # ── evaluator-only fields ───────────────────────────────────────────────
    ground_truth_group_id: str   # e.g. "GRP-00042" — evaluator only
    event_id: str                # internal only — never reaches matcher

    # ── per-source opaque IDs (what the matcher actually sees) ──────────────
    # Generated independently so there is NO lexical link between them.
    bank_source_event_id: str    # e.g. "BNK-7f3a2c..." — opaque
    invoice_source_event_id: str # e.g. "INV-9b1d4e..." — opaque
    gateway_source_event_id: str # e.g. "GWY-2e8f01..." — opaque

    # ── economic facts ──────────────────────────────────────────────────────
    merchant_name: str
    counterparty: str
    amount_minor_units: int      # gross invoice amount in paise
    currency: str                # 'INR'
    invoice_date: date
    settlement_date: date
    reference: str               # e.g. 'INV-2024-001234'
    description: str
    lifecycle_state: str

    # ── gateway fee breakdown ───────────────────────────────────────────────
    gateway_fee_minor: int       # ~2.3% of gross
    gateway_tax_minor: int       # ~18% GST on fee
    gateway_net_minor: int       # gross − fee − tax

    # ── special case flags ──────────────────────────────────────────────────
    is_partial: bool
    partial_outstanding_minor: int
    is_duplicate_delivery: bool  # BANK record emitted twice, same source_event_id
    is_control_conflict: bool    # gateway net deliberately wrong → triggers CTRL-004


class EconomicEventGenerator:
    """
    Generates a list of EconomicEvent dataclasses.

    Determinism: Faker.seed() + random.Random(seed_int) ensures identical
    output for the same seed string every run.
    """

    # Merchant categories for realistic Indian e-commerce/SaaS data
    _CATEGORIES = ['e-commerce', 'SaaS', 'retail', 'logistics', 'edtech']

    def __init__(self, config: GeneratorConfig):
        self.config = config
        seed_int = int(hashlib.md5(config.seed.encode()).hexdigest(), 16) % (2 ** 32)
        Faker.seed(seed_int)
        self.fake = Faker('en_IN')
        self.rng = random.Random(seed_int)
        # Separate RNG for ID generation so ID generation is independent of
        # data-field generation — prevents accidental coupling.
        self.id_rng = random.Random(seed_int ^ 0xDEADBEEF)

    def _opaque_id(self, prefix: str) -> str:
        """
        Generate an opaque, unguessable source_event_id.
        Uses a seeded UUID so it's deterministic but has no lexical link
        to the underlying event_id.
        """
        raw = self.id_rng.getrandbits(128)
        uid = uuid.UUID(int=raw)
        return f"{prefix}-{str(uid)[:8].upper()}"

    def generate(self) -> list[EconomicEvent]:
        events: list[EconomicEvent] = []
        num = self.config.num_events

        # Build the role distribution
        roles: list[str] = []
        roles.extend(['partial']  * max(3, int(num * self.config.partial_payment_rate)))
        roles.extend(['refund']   * max(2, int(num * self.config.refund_rate)))
        roles.extend(['reversed'] * 1)
        roles.extend(['duplicate'] * max(1, int(num * self.config.duplicate_delivery_rate)))
        roles.extend(['control']  * 1)  # exactly one deliberate control-conflict case
        roles.extend(['settled']  * (num - len(roles)))
        self.rng.shuffle(roles)

        for i, role in enumerate(roles[:num]):
            # ── IDs ──────────────────────────────────────────────────────────
            event_id = f"EVT-{i + 1:05d}"             # internal only
            ground_truth_group_id = f"GRP-{i + 1:05d}"  # evaluator only

            # Three independent opaque IDs — no lexical link between them or
            # to event_id. A matcher joining on ID substring cannot solve this.
            bank_sid    = self._opaque_id("BNK")
            invoice_sid = self._opaque_id("INV")
            gateway_sid = self._opaque_id("GWY")

            # ── Merchant data ─────────────────────────────────────────────────
            merchant_name = self.fake.company()
            counterparty  = self.fake.name()

            # ── Financial facts ───────────────────────────────────────────────
            amount_minor_units = self.rng.randint(50_000, 20_000_000)  # ₹500–₹2L in paise
            currency = 'INR'
            invoice_date    = self.fake.date_between(start_date='-1y', end_date='-7d')
            settlement_date = invoice_date + timedelta(days=self.rng.randint(1, 3))
            reference   = f"INV-{invoice_date.year}-{self.rng.randint(100000, 999999)}"
            description = self.fake.sentence(nb_words=6)

            # ── Gateway fee breakdown ─────────────────────────────────────────
            gateway_fee_minor = round(amount_minor_units * 0.023)
            gateway_tax_minor = round(gateway_fee_minor * 0.18)
            gateway_net_minor = amount_minor_units - gateway_fee_minor - gateway_tax_minor

            # ── Role-specific flags ───────────────────────────────────────────
            lifecycle_state       = 'SETTLED'
            is_partial            = False
            partial_outstanding   = 0
            is_duplicate_delivery = False
            is_control_conflict   = False

            if role == 'partial':
                is_partial = True
                partial_outstanding = self.rng.randint(1_000, amount_minor_units // 2)
                lifecycle_state = 'PARTIALLY_SETTLED'
            elif role == 'refund':
                lifecycle_state = 'REFUNDED'
            elif role == 'reversed':
                lifecycle_state = 'REVERSED'
            elif role == 'duplicate':
                is_duplicate_delivery = True
            elif role == 'control':
                is_control_conflict = True

            events.append(EconomicEvent(
                ground_truth_group_id=ground_truth_group_id,
                event_id=event_id,
                bank_source_event_id=bank_sid,
                invoice_source_event_id=invoice_sid,
                gateway_source_event_id=gateway_sid,
                merchant_name=merchant_name,
                counterparty=counterparty,
                amount_minor_units=amount_minor_units,
                currency=currency,
                invoice_date=invoice_date,
                settlement_date=settlement_date,
                reference=reference,
                description=description,
                lifecycle_state=lifecycle_state,
                gateway_fee_minor=gateway_fee_minor,
                gateway_tax_minor=gateway_tax_minor,
                gateway_net_minor=gateway_net_minor,
                is_partial=is_partial,
                partial_outstanding_minor=partial_outstanding,
                is_duplicate_delivery=is_duplicate_delivery,
                is_control_conflict=is_control_conflict,
            ))

        return events
