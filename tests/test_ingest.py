"""
tests/test_ingest.py — Tests IngestService logic without a live DB.
Uses a lightweight in-memory mock session to verify validation and dedup logic.
"""
import sys
import asyncio
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from sqlalchemy.exc import IntegrityError
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from app.ingest import IngestService


def make_valid_record(**overrides):
    base = {
        'source': 'BANK',
        'source_event_id': 'BNK-AABBCCDD',
        'amount_minor_units': 100000,
        'currency': 'INR',
        'reference': 'INV-2024-001234',
        'counterparty': 'NEFT CR ACME',
        'description': 'Settlement',
        'transaction_date': '2024-06-15',
        'lifecycle_state': 'SETTLED',
        'raw_payload': {},
    }
    base.update(overrides)
    return base


def make_ingest_service():
    """Return an IngestService backed by a mock DB session."""
    mock_session = MagicMock()
    mock_session.execute = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()
    return IngestService(mock_session, run_id='run-test-001'), mock_session


def ingest_sync(svc, records):
    """Call ingest() — works with the mock session which is synchronous."""
    result = svc.ingest(records)
    # If it returned a coroutine (real async session), run it
    import asyncio, inspect
    if inspect.iscoroutine(result):
        return asyncio.run(result)
    return result


class TestIngestService:
    def test_valid_record_is_accepted(self):
        svc, db = make_ingest_service()
        result = ingest_sync(svc, [make_valid_record()])
        assert result['accepted'] == 1
        assert result['rejected'] == 0
        assert result['deduplicated'] == 0

    def test_ground_truth_group_id_is_stripped(self):
        """ground_truth_group_id must be popped before any DB call."""
        svc, db = make_ingest_service()
        rec = make_valid_record()
        rec['ground_truth_group_id'] = 'GRP-00001'
        ingest_sync(svc, [rec])
        # Verify the INSERT call params never contain ground_truth_group_id
        call_args = db.execute.call_args
        if call_args:
            params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
            assert 'ground_truth_group_id' not in str(params)

    def test_invalid_source_is_rejected(self):
        svc, _ = make_ingest_service()
        result = ingest_sync(svc, [make_valid_record(source='WIRE')])
        assert result['rejected'] == 1
        assert any('source' in r.lower() for r in result['rejected_reasons'])

    def test_invalid_lifecycle_state_is_rejected(self):
        svc, _ = make_ingest_service()
        result = ingest_sync(svc, [make_valid_record(lifecycle_state='PENDING')])
        assert result['rejected'] == 1

    def test_zero_amount_is_rejected(self):
        svc, _ = make_ingest_service()
        result = ingest_sync(svc, [make_valid_record(amount_minor_units=0)])
        assert result['rejected'] == 1

    def test_negative_amount_is_rejected(self):
        svc, _ = make_ingest_service()
        result = ingest_sync(svc, [make_valid_record(amount_minor_units=-500)])
        assert result['rejected'] == 1

    def test_wrong_currency_length_rejected(self):
        svc, _ = make_ingest_service()
        result = ingest_sync(svc, [make_valid_record(currency='INRR')])
        assert result['rejected'] == 1

    def test_duplicate_increments_deduplicated_not_raises(self):
        """IntegrityError on unique constraint → deduplicated += 1, no exception."""
        svc, db = make_ingest_service()
        db.execute.side_effect = [
            None,                                  # first call: accepted
            IntegrityError(None, None, None),      # second call: duplicate
        ]
        result = ingest_sync(svc, [make_valid_record(), make_valid_record()])
        assert result['accepted'] == 1
        assert result['deduplicated'] == 1
        assert result['rejected'] == 0

    def test_counts_sum_to_total(self):
        """accepted + deduplicated + rejected == total records."""
        svc, db = make_ingest_service()
        db.execute.side_effect = [
            None,
            IntegrityError(None, None, None),
        ]
        records = [
            make_valid_record(source_event_id='A'),
            make_valid_record(source_event_id='A'),   # duplicate
            make_valid_record(source='INVALID'),       # rejected
        ]
        result = ingest_sync(svc, records)
        total = result['accepted'] + result['deduplicated'] + result['rejected']
        assert total == len(records)

    def test_all_three_sources_accepted(self):
        """BANK, INVOICE, GATEWAY all pass source validation."""
        svc, _ = make_ingest_service()
        records = [
            make_valid_record(source='BANK',    source_event_id='B1'),
            make_valid_record(source='INVOICE', source_event_id='I1', lifecycle_state='CAPTURED'),
            make_valid_record(source='GATEWAY', source_event_id='G1'),
        ]
        result = ingest_sync(svc, records)
        assert result['accepted'] == 3
        assert result['rejected'] == 0
