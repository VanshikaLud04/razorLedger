from fastapi import APIRouter, Depends
from app.schemas import ReconcileRunRequest, ReconcileRunResponse, RunScorecard
import uuid

router = APIRouter()

def get_db():
    pass

async def pipeline_orchestrator(run_id: str):
    # Pipeline: ingest -> blocking -> deterministic match -> fuzzy evidence -> probabilistic -> allocation -> controls -> decision -> audit.
    pass

@router.post("/reconcile/run", response_model=ReconcileRunResponse)
async def run_reconcile(request: ReconcileRunRequest, db=Depends(get_db)):
    run_id = uuid.uuid4()
    # Creates a runs row, triggers reconciliation pipeline
    # For P0, simple async function call
    await pipeline_orchestrator(str(run_id))
    return ReconcileRunResponse(run_id=run_id, status="RUNNING")

@router.get("/reconcile/{run_id}/results", response_model=RunScorecard)
async def get_results(run_id: str, db=Depends(get_db)):
    # Query decisions, allocations, control_results for this run_id.
    # Compute scorecard fields.
    # Mocking for now as per P0/P1 instructions.
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
