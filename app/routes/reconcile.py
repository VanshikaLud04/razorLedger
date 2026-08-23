from fastapi import APIRouter, Depends
from app.schemas import ReconcileRunRequest, ReconcileRunResponse, RunScorecard
import uuid
import asyncio

router = APIRouter()

# In-memory store for P2 UI demo
_RUNS = {}

def get_db():
    pass

@router.post("/reconcile/run", response_model=ReconcileRunResponse)
async def run_reconcile(request: ReconcileRunRequest, db=Depends(get_db)):
    run_id = uuid.uuid4()
    _RUNS[str(run_id)] = {"status": "RUNNING", "result": None, "metrics": None, "partition": request.dataset_partition}
    
    # Run pipeline in background
    asyncio.create_task(run_pipeline_background(str(run_id), request.dataset_partition))
    
    return ReconcileRunResponse(run_id=run_id, status="RUNNING")

async def run_pipeline_background(run_id: str, partition: str):
    from scripts.run_e2e import run_pipeline, evaluate
    from generator.config import PARTITION_SEEDS
    
    seed = PARTITION_SEEDS.get(partition, "razorledger-dev-v1")
    # For UI demo, let's execute it synchronously in this thread
    # In a real app this would be Celery or similar
    try:
        # Just run the pipeline!
        result, truth = run_pipeline(seed=seed, partition=partition, label=partition)
        metrics = evaluate(result, truth)
        _RUNS[run_id]["result"] = result
        _RUNS[run_id]["metrics"] = metrics
        _RUNS[run_id]["status"] = "COMPLETE"
    except Exception as e:
        print(f"Pipeline error: {e}")
        _RUNS[run_id]["status"] = "FAILED"

@router.get("/reconcile/{run_id}/results", response_model=RunScorecard)
async def get_results(run_id: str, db=Depends(get_db)):
    run_data = _RUNS.get(run_id)
    if not run_data or run_data["status"] != "COMPLETE":
        return RunScorecard(
            run_id=uuid.UUID(run_id),
            records_total=0,
            auto_resolved=0,
            review=0,
            no_match=0,
            pending=0,
            value_covered_minor=0,
            value_verified_minor=0,
            unsafe_automation_pct=0.0,
            review_burden_pct=0.0,
            adversarial_holdout=None,
            ablation=None
        )
        
    result = run_data["result"]
    metrics = run_data["metrics"]
    
    return RunScorecard(
        run_id=uuid.UUID(run_id),
        records_total=result.total_source_records,
        auto_resolved=result.auto_resolved,
        review=result.review_count,
        no_match=result.no_match_count,
        pending=result.pending_count,
        value_covered_minor=metrics["verified_value_minor"],
        value_verified_minor=metrics["verified_value_minor"],
        unsafe_automation_pct=metrics["false_auto_match_rate"],
        review_burden_pct=result.review_rate,
        adversarial_holdout=None,
        ablation=None
    )
