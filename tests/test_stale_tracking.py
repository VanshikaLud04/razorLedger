import pytest
from datetime import datetime, timezone, timedelta
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

@pytest.fixture(autouse=True)
def reset_globals():
    _RUNS.clear()
    _RESOLVED_ITEMS.clear()
    yield
    _RUNS.clear()
    _RESOLVED_ITEMS.clear()

def setup_mock_run(created_at: datetime):
    run_id = str(uuid4())
    decisions = [
        MockDecision("REVIEW", 1000, "BANK-1"),
        MockDecision("MATCH", 2000, "GATEWAY-1")
    ]
    _RUNS[run_id] = {
        "status": "COMPLETE",
        "result": MockPipelineResult(decisions),
        "created_at": created_at
    }
    return run_id

def test_stale_tracking_0m():
    now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    setup_mock_run(now)
    
    with patch("app.routes.review.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        
        response = client.get("/review-queue")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_open"] == 1
        item = data["items"][0]
        assert item["age_seconds"] == 0
        assert item["is_stale"] is False
        assert item["age_label"] == "0m"

def test_stale_tracking_1h():
    created = datetime(2026, 8, 24, 11, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    setup_mock_run(created)
    
    with patch("app.routes.review.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        
        response = client.get("/review-queue")
        data = response.json()
        item = data["items"][0]
        assert item["age_seconds"] == 3600
        assert item["is_stale"] is False
        assert item["age_label"] == "1h"

def test_stale_tracking_exactly_24h():
    created = datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    setup_mock_run(created)
    
    with patch("app.routes.review.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        
        response = client.get("/review-queue")
        data = response.json()
        item = data["items"][0]
        assert item["age_seconds"] == 86400
        assert item["is_stale"] is False
        assert item["age_label"] == "1d 0h"

def test_stale_tracking_24h_plus_1s():
    created = datetime(2026, 8, 23, 11, 59, 59, tzinfo=timezone.utc)
    now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    setup_mock_run(created)
    
    with patch("app.routes.review.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        
        response = client.get("/review-queue")
        data = response.json()
        item = data["items"][0]
        assert item["age_seconds"] == 86401
        assert item["is_stale"] is True
        assert item["age_label"] == "1d 0h"

def test_stale_tracking_48h():
    created = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    setup_mock_run(created)
    
    with patch("app.routes.review.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        
        response = client.get("/review-queue")
        data = response.json()
        item = data["items"][0]
        assert item["age_seconds"] == 172800
        assert item["is_stale"] is True
        assert item["age_label"] == "2d 0h"

def test_stale_tracking_future_timestamp_clamps_to_zero():
    created = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    setup_mock_run(created)
    
    with patch("app.routes.review.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        
        response = client.get("/review-queue")
        data = response.json()
        item = data["items"][0]
        assert item["age_seconds"] == 0
        assert item["is_stale"] is False
        assert item["age_label"] == "0m"

def test_resolved_items_omitted_from_queue():
    now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    setup_mock_run(now)
    
    with patch("app.routes.review.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        
        # Initially 1 open
        response = client.get("/review-queue")
        assert response.json()["total_open"] == 1
        item_id = response.json()["items"][0]["id"]
        
        # Resolve it
        res = client.post(f"/review/{item_id}/resolve", json={"resolver": "test_user"})
        assert res.status_code == 200
        
        # Now 0 open
        response2 = client.get("/review-queue")
        assert response2.json()["total_open"] == 0
