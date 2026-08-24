import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.routes.reconcile import _RUNS

class MockGroqProvider:
    def __init__(self, *args, **kwargs):
        pass
    def generate(self, prompt, schema_class, max_attempts, run_id, batch_size):
        return True, '{"explanation": "mock"}', 0, 0, 0, "mock"
    def generate_batch(self, groups, run_id):
        return {}
    def should_invoke(self, ranked, index):
        return False

@pytest.fixture(autouse=True)
def mock_groq():
    with patch("app.matching.llm.GroqProvider", MockGroqProvider):
        with patch("app.matching.llm.LLMEvidenceGenerator.should_invoke", return_value=False):
            yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_replay_safety_and_diffs(client):
    # 1. Trigger an actual run so we have a valid baseline
    res = client.post("/reconcile/run", json={
        "dataset_seed": "razorledger-dev-v1",
        "dataset_partition": "DEV",
        "thresholds": {},
        "embedding_model": "test",
        "llm_model": "test",
        "prompt_version": "test"
    })
    assert res.status_code == 200
    run_id = res.json()["run_id"]
    
    # 2. Wait for it to complete in memory
    import time
    for _ in range(60):
        if _RUNS[run_id]["status"] == "COMPLETE":
            break
        elif _RUNS[run_id]["status"] == "FAILED":
            raise Exception("Run failed in background")
        time.sleep(0.5)
        
    assert _RUNS[run_id]["status"] == "COMPLETE"
    baseline = _RUNS[run_id]["result"]
    baseline_match = baseline.auto_resolved
    
    # 3. Hit Replay endpoint with a much lower threshold
    replay_res = client.post("/reconcile/replay", json={
        "run_id": run_id,
        "auto_match_threshold": 0.40,
        "review_threshold": 0.10
    })
    
    assert replay_res.status_code == 200, replay_res.text
    data = replay_res.json()
    
    assert data["warning_label"] == "SIMULATION ONLY - NO PRODUCTION STATE CHANGED"
    assert data["baseline_config"]["auto_match_threshold"] == 0.80
    assert data["replay_config"]["auto_match_threshold"] == 0.40
    
    # Replay auto_resolved should be equal or higher because threshold is lower
    assert data["replay_scorecard"]["auto_resolved"] >= data["baseline_scorecard"]["auto_resolved"]
    
    # 4. Verify Original Run Data was NOT mutated
    assert _RUNS[run_id]["result"] is baseline
    assert _RUNS[run_id]["result"].auto_resolved == baseline_match
    
    # Verify we got some promoted items
    if data["replay_scorecard"]["auto_resolved"] > data["baseline_scorecard"]["auto_resolved"]:
        assert len(data["promoted"]) > 0
        diff = data["promoted"][0]
        assert diff["baseline_action"] == "REVIEW"
        assert diff["replay_action"] == "MATCH"
        
    # Verify Stage F still blocks appropriately
    for d in data["unchanged"]:
        if "FAIL" in d["control_result"]:
            assert d["stage_f_status"] == "REJECTED"
            
def test_replay_invalid_run(client):
    res = client.post("/reconcile/replay", json={
        "run_id": "00000000-0000-0000-0000-000000000000",
        "auto_match_threshold": 0.50,
        "review_threshold": 0.20
    })
    # Should throw HTTPException which fastapi might return as 404
    assert res.status_code == 404

if __name__ == "__main__":
    test_replay_safety_and_diffs()
    test_replay_invalid_run()
    print("ALL TESTS PASSED")
