import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app as main_app
from app.routes.reconcile import _RUNS
from app.routes.review import _RESOLVED_ITEMS
from app.db import get_db
import app.matching.llm

async def override_get_db():
    return None

main_app.dependency_overrides[get_db] = override_get_db

class MockGroqProvider:
    def __init__(self, *args, **kwargs):
        pass
    def generate(self, prompt, schema_class, max_attempts, run_id, batch_size):
        if "test_fail" in prompt:
            return False, "", 0, 0, 0, "mock"
        return True, '{"explanation": "Mocked explanation."}', 0, 0, 0, "mock"

import app.routes.qa
app.routes.qa.GroqProvider = MockGroqProvider

client = TestClient(main_app)

class MockPipelineResult:
    def __init__(self, decisions):
        self.decisions = decisions

class MockDecision:
    def __init__(self, action, source_event_id, provisional_action=None, primary_reason=None, control_result=None):
        self.action = action
        self.source_event_id = source_event_id
        self.provisional_action = provisional_action
        self.primary_reason = primary_reason
        self.control_result = control_result

@pytest.fixture(autouse=True)
def reset_globals():
    _RUNS.clear()
    _RESOLVED_ITEMS.clear()
    yield
    _RUNS.clear()
    _RESOLVED_ITEMS.clear()

def setup_mock_run():
    decisions = [
        MockDecision("REVIEW", "GWY-1", provisional_action="MATCH", primary_reason="Multiple matches", control_result="CTRL-001 FAIL"),
        MockDecision("PENDING", "BANK-1", provisional_action="PENDING", primary_reason="Within settlement window", control_result="N/A"),
        MockDecision("REVIEW", "INV-1", provisional_action="REVIEW", primary_reason="No matches found", control_result="N/A"),
    ]
    
    _RUNS["test-run"] = {
        "id": "test-run",
        "status": "COMPLETE",
        "result": MockPipelineResult(decisions),
        "created_at": datetime.now(timezone.utc)
    }

def test_qa_record_explanation_review():
    setup_mock_run()
    resp = client.post("/qa", json={"question": "Why is this in REVIEW?", "entity_id": "GWY-1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounding"] in ["GROUNDED", "PROVIDER_UNAVAILABLE"]
    assert data["question_type"] == "RECORD_EXPLANATION"
    
    facts = {f["label"]: f["value"] for f in data["facts"]}
    assert facts["Provisional decision"] == "MATCH"
    assert facts["Final decision"] == "REVIEW"
    assert facts["Reason"] == "Multiple matches"
    assert facts["Control result"] == "CTRL-001 FAIL"
    
def test_qa_control_explanation():
    setup_mock_run()
    resp = client.post("/qa", json={"question": "Which control blocked this?", "entity_id": "GWY-1"})
    data = resp.json()
    assert data["question_type"] == "CONTROL_EXPLANATION"
    
    # Check that CTRL-001 was extracted as a source
    sources = [s["id"] for s in data["sources"]]
    assert "CTRL-001" in sources

def test_qa_pending_review_counts():
    setup_mock_run()
    resp = client.post("/qa", json={"question": "How many records are PENDING?"})
    data = resp.json()
    assert data["question_type"] == "PENDING_REVIEW"
    facts = {f["label"]: f["value"] for f in data["facts"]}
    assert facts["Pending records"] == "1"
    assert facts["Open reviews"] == "2"

def test_qa_insufficient_data_missing_entity():
    setup_mock_run()
    resp = client.post("/qa", json={"question": "Why is this in REVIEW?", "entity_id": "UNKNOWN-999"})
    data = resp.json()
    assert data["grounding"] == "INSUFFICIENT_DATA"
    assert "not found" in data["answer"].lower()

def test_qa_audit_verification():
    setup_mock_run()
    resp = client.post("/qa", json={"question": "Is the audit chain valid?", "entity_id": "GWY-1"})
    data = resp.json()
    assert data["question_type"] == "AUDIT"
    facts = {f["label"]: f["value"] for f in data["facts"]}
    assert "Audit chain verified" in facts
