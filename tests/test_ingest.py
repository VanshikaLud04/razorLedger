import pytest
import asyncio
from app.ingest import IngestService
from sqlalchemy.exc import IntegrityError

class MockDB:
    def __init__(self):
        self.records = []
        self.should_fail_unique = False

    def execute(self, stmt, params):
        if self.should_fail_unique:
            raise IntegrityError("unique constraint", params, None)
        self.records.append(params)

    def commit(self):
        pass

    def rollback(self):
        pass

class TestIngest:
    @pytest.mark.asyncio
    async def test_duplicate_source_event_id_is_deduplicated(self):
        db = MockDB()
        db.should_fail_unique = True
        service = IngestService(db, "run1")
        res = await service.ingest([{"source": "BANK", "source_event_id": "1", "amount_minor_units": 100, "currency": "USD", "transaction_date": "2023-01-01", "lifecycle_state": "SETTLED"}])
        assert res["deduplicated"] == 1
        assert res["accepted"] == 0

    @pytest.mark.asyncio
    async def test_invalid_currency_is_rejected(self):
        db = MockDB()
        service = IngestService(db, "run1")
        res = await service.ingest([{"source": "BANK", "source_event_id": "1", "amount_minor_units": 100, "currency": "US", "transaction_date": "2023-01-01", "lifecycle_state": "SETTLED"}])
        assert res["rejected"] == 1

    @pytest.mark.asyncio
    async def test_negative_amount_is_rejected(self):
        db = MockDB()
        service = IngestService(db, "run1")
        res = await service.ingest([{"source": "BANK", "source_event_id": "1", "amount_minor_units": -100, "currency": "USD", "transaction_date": "2023-01-01", "lifecycle_state": "SETTLED"}])
        assert res["rejected"] == 1

    @pytest.mark.asyncio
    async def test_invalid_lifecycle_state_is_rejected(self):
        db = MockDB()
        service = IngestService(db, "run1")
        res = await service.ingest([{"source": "BANK", "source_event_id": "1", "amount_minor_units": 100, "currency": "USD", "transaction_date": "2023-01-01", "lifecycle_state": "INVALID"}])
        assert res["rejected"] == 1

    @pytest.mark.asyncio
    async def test_ground_truth_group_id_is_stripped_on_ingest(self):
        db = MockDB()
        service = IngestService(db, "run1")
        await service.ingest([{"source": "BANK", "source_event_id": "1", "amount_minor_units": 100, "currency": "USD", "transaction_date": "2023-01-01", "lifecycle_state": "SETTLED", "ground_truth_group_id": "G1"}])
        assert "ground_truth_group_id" not in db.records[0]

    @pytest.mark.asyncio
    async def test_accepted_plus_deduped_plus_rejected_equals_total(self):
        db = MockDB()
        service = IngestService(db, "run1")
        records = [
            {"source": "BANK", "source_event_id": "1", "amount_minor_units": 100, "currency": "USD", "transaction_date": "2023-01-01", "lifecycle_state": "SETTLED"},
            {"source": "BANK", "source_event_id": "2", "amount_minor_units": -10, "currency": "USD", "transaction_date": "2023-01-01", "lifecycle_state": "SETTLED"}
        ]
        res = await service.ingest(records)
        assert res["accepted"] + res["deduplicated"] + res["rejected"] == len(records)
