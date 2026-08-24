import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.routes.reconcile import _RUNS
from app.routes.review import _RESOLVED_ITEMS

client = TestClient(app)

class MockPipelineResult:
    def __init__(self, decisions):
        self.decisions = decisions

class MockDecision:
    def __init__(self, action, amount, source_event_id="BANK-1"):
        self.action = action
        self.amount_minor_units = amount
        self.source_event_id = source_event_id
        self.primary_reason = "REASON"
        self.control_result = "FAIL"
        self.source = source_event_id.split('-')[0]

@pytest.fixture(autouse=True)
def reset_globals():
    _RUNS.clear()
    _RESOLVED_ITEMS.clear()
    yield
    _RUNS.clear()
    _RESOLVED_ITEMS.clear()

def setup_mock_run():
    run_id = str(uuid4())
    decisions = [
        MockDecision("REVIEW", 15050, "BANK-1"),
        MockDecision("REVIEW", 30000, "GATEWAY-2")
    ]
    _RUNS[run_id] = {
        "status": "COMPLETE",
        "result": MockPipelineResult(decisions),
        "created_at": datetime.now(timezone.utc)
    }
    return run_id

def test_journal_recommendation_amount_and_currency_preservation():
    setup_mock_run()
    response = client.get("/review-queue")
    assert response.status_code == 200
    data = response.json()
    
    # BANK item
    bank_item = next(i for i in data["items"] if "BANK" in i["source_record"]["source_event_id"])
    journal = bank_item["proposed_journal"]
    assert journal is not None
    assert len(journal["lines"]) == 2
    
    # Verify amounts
    for line in journal["lines"]:
        assert line["amount_minor_units"] == 15050
        assert line["currency"] == "INR"

def test_journal_recommendation_manual_selection_fallback():
    setup_mock_run()
    response = client.get("/review-queue")
    data = response.json()
    
    for item in data["items"]:
        journal = item["proposed_journal"]
        for line in journal["lines"]:
            # Our implementation always forces manual selection since no authoritative mapping exists
            assert line["account"] == "MANUAL ACCOUNT SELECTION REQUIRED"

def test_journal_recommendation_balanced_output():
    setup_mock_run()
    response = client.get("/review-queue")
    data = response.json()
    
    for item in data["items"]:
        journal = item["proposed_journal"]
        debits = sum(l["amount_minor_units"] for l in journal["lines"] if l["type"] == "DEBIT")
        credits = sum(l["amount_minor_units"] for l in journal["lines"] if l["type"] == "CREDIT")
        assert debits == credits
        assert debits > 0

def test_journal_recommendation_explicit_approval_required():
    setup_mock_run()
    response = client.get("/review-queue")
    data = response.json()
    
    for item in data["items"]:
        journal = item["proposed_journal"]
        assert journal["approval_requirement"] == "RECOMMENDATION — REQUIRES OPERATOR APPROVAL"

def test_journal_recommendation_does_not_alter_state():
    setup_mock_run()
    response = client.get("/review-queue")
    data = response.json()
    
    # Still PENDING/REVIEW conceptually
    # total_open should be 2
    assert data["total_open"] == 2
    for item in data["items"]:
        assert item["id"] not in _RESOLVED_ITEMS
