"""
generator/views.py — Source view derivation.

Takes a list of EconomicEvent records and produces the flat list of
source_record dicts that will be ingested by app/ingest.py.

OUTPUT RULES:
  - Each dict has all SourceRecordIn fields + 'ground_truth_group_id'.
  - 'ground_truth_group_id' is tagged for strip-on-ingest: the ingest
    layer reads it into the truth store and removes it before writing
    to source_records. It never enters app/.
  - source_event_ids are the OPAQUE ones from EconomicEvent — no event_id.
  - 150 economic events → ~450 source records (+ 1 extra for duplicate).
  - "150 records" in the brief = 150 underlying economic events.
"""

import random
import hashlib
from datetime import timedelta

from .config import GeneratorConfig
from .events import EconomicEvent
from .corruption import apply_corruption
from .truth import GroundTruthBundle, GroundTruthRecord


class SourceViewDeriver:
    """
    Derives three source representations (BANK, INVOICE, GATEWAY) from
    each EconomicEvent.

    Also builds and returns a GroundTruthBundle for evaluator use.
    The bundle must NOT be passed into the matching pipeline.
    """

    def __init__(self, config: GeneratorConfig):
        self.config = config
        seed_int = int(hashlib.md5(config.seed.encode()).hexdigest(), 16) % (2 ** 32)
        # Offset so this RNG stream is independent from events.py
        self.rng = random.Random(seed_int ^ 0xCAFEBABE)

    def derive(
        self,
        events: list[EconomicEvent],
    ) -> tuple[list[dict], GroundTruthBundle]:
        """
        Returns:
            records: flat list of source_record dicts (ready for ingest)
            truth:   GroundTruthBundle — evaluator only, must not reach app/
        """
        records: list[dict] = []
        truth = GroundTruthBundle()

        for event in events:
            # ── 1. INVOICE ────────────────────────────────────────────────────
            # Invoice: clean data, no corruption — authoritative gross amount.
            inv_record = {
                'ground_truth_group_id': event.ground_truth_group_id,  # stripped on ingest
                'source': 'INVOICE',
                'source_event_id': event.invoice_source_event_id,      # opaque
                'amount_minor_units': event.amount_minor_units,        # gross
                'currency': event.currency,
                'reference': event.reference,                          # clean
                'counterparty': event.merchant_name,                   # merchant, not payer
                'description': f"Invoice: {event.description}",
                'transaction_date': event.invoice_date,
                'lifecycle_state': 'PARTIALLY_SETTLED' if event.is_partial else 'CAPTURED',
                'raw_payload': {
                    'merchant_category': self.rng.choice(
                        ['e-commerce', 'SaaS', 'retail', 'logistics', 'edtech']
                    ),
                    **(
                        {'outstanding_minor': event.partial_outstanding_minor}
                        if event.is_partial else {}
                    ),
                },
            }
            records.append(inv_record)
            truth.records.append(GroundTruthRecord(
                ground_truth_group_id=event.ground_truth_group_id,
                economic_event_id=event.event_id,
                source='INVOICE',
                source_event_id=event.invoice_source_event_id,
                is_partial=event.is_partial,
            ))

            # ── 2. GATEWAY ────────────────────────────────────────────────────
            # Gateway: net amount (gross − fee − tax); reference may be corrupted.
            # CTRL-004 test: is_control_conflict → gateway net is deliberately wrong.
            gateway_amount = event.gateway_net_minor
            if event.is_control_conflict:
                gateway_amount += 500   # ₹5 deliberate discrepancy → CTRL-004 fires

            gw_record = {
                'ground_truth_group_id': event.ground_truth_group_id,
                'source': 'GATEWAY',
                'source_event_id': event.gateway_source_event_id,     # opaque
                'amount_minor_units': gateway_amount,
                'currency': event.currency,
                'reference': apply_corruption(
                    event.reference, self.config.corruption_rate, self.rng
                ),
                'counterparty': event.merchant_name,
                'description': f"Gateway settlement: {event.description}",
                'transaction_date': event.settlement_date,
                'lifecycle_state': event.lifecycle_state,
                'raw_payload': {
                    'gateway_fee_minor': event.gateway_fee_minor,
                    'gateway_tax_minor': event.gateway_tax_minor,
                    'gateway_gross_minor': event.amount_minor_units,
                    'is_control_conflict': event.is_control_conflict,
                },
            }
            records.append(gw_record)
            truth.records.append(GroundTruthRecord(
                ground_truth_group_id=event.ground_truth_group_id,
                economic_event_id=event.event_id,
                source='GATEWAY',
                source_event_id=event.gateway_source_event_id,
                is_control_conflict=event.is_control_conflict,
            ))

            # ── 3. BANK ───────────────────────────────────────────────────────
            # Bank: actual credit; heavier corruption, bank-style narration.
            # Date may lag settlement by 0–2 days.
            bank_date = event.settlement_date + timedelta(days=self.rng.randint(0, 2))
            bank_ref = apply_corruption(
                event.reference,
                min(self.config.corruption_rate * 1.5, 0.95),
                self.rng,
            )
            bank_record = {
                'ground_truth_group_id': event.ground_truth_group_id,
                'source': 'BANK',
                'source_event_id': event.bank_source_event_id,        # opaque
                'amount_minor_units': event.gateway_net_minor,        # bank sees net (always clean)
                'currency': event.currency,
                'reference': bank_ref,
                'counterparty': f"NEFT CR {event.merchant_name[:12].upper()}",
                'description': f"Cr by {event.counterparty} via IMPS",
                'transaction_date': bank_date,
                'lifecycle_state': 'SETTLED',
                'raw_payload': {'bank_channel': self.rng.choice(['NEFT', 'IMPS', 'RTGS'])},
            }
            records.append(bank_record)
            truth.records.append(GroundTruthRecord(
                ground_truth_group_id=event.ground_truth_group_id,
                economic_event_id=event.event_id,
                source='BANK',
                source_event_id=event.bank_source_event_id,
                is_duplicate_delivery=event.is_duplicate_delivery,
            ))

            # ── 4. Duplicate delivery (idempotency test) ──────────────────────
            # The SAME bank record is emitted a second time with the SAME
            # source_event_id. The UNIQUE(run_id, source, source_event_id)
            # constraint must catch this — no second allocation created.
            if event.is_duplicate_delivery:
                duplicate = bank_record.copy()
                # raw_payload gets a marker so we can verify in tests
                duplicate['raw_payload'] = {
                    **bank_record['raw_payload'],
                    '_is_duplicate': True,
                }
                records.append(duplicate)

        return records, truth
