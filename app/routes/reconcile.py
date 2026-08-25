from fastapi import APIRouter, Depends
from app.schemas import ReconcileRunRequest, ReconcileRunResponse, RunScorecard, ReplayRequest, ReplayResponse
import uuid
import asyncio
import csv
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/final_metrics")
async def get_final_metrics():
    # Read from final artifacts
    delta_file = Path("reports/final/FINAL_DELTA_TABLE.csv")
    if not delta_file.exists():
        return {"error": "Final metrics not yet generated"}
        
    metrics = {}
    with open(delta_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics[row['Metric']] = {
                'Original_P1': float(row['Original_P1']),
                'Final_P7': float(row['Final_P7']),
                'Absolute_Delta': float(row['Absolute_Delta'])
            }
            
    # Read scorecard partitions
    scorecard = Path("reports/final/FINAL_SCORECARD.csv")
    partitions = []
    if scorecard.exists():
        with open(scorecard, "r") as f:
            reader = csv.DictReader(f)
            partitions = [row for row in reader]
            
    return {"delta": metrics, "partitions": partitions}

# In-memory store for P2 UI demo
_RUNS = {}

def get_db():
    pass

@router.post("/reconcile/run", response_model=ReconcileRunResponse)
async def run_reconcile(request: ReconcileRunRequest, db=Depends(get_db)):
    run_id = uuid.uuid4()
    from datetime import datetime, timezone
    _RUNS[str(run_id)] = {"status": "RUNNING", "result": None, "metrics": None, "partition": request.dataset_partition, "created_at": datetime.now(timezone.utc)}
    
    # Run pipeline in background
    asyncio.create_task(run_pipeline_background(str(run_id), request.dataset_partition))
    
    return ReconcileRunResponse(run_id=run_id, status="RUNNING")

async def run_pipeline_background(run_id: str, partition: str):
    from scripts.run_e2e import run_pipeline, evaluate
    from generator.config import PARTITION_SEEDS
    import anyio
    
    seed = PARTITION_SEEDS.get(partition, "razorledger-dev-v1")
    try:
        # Run CPU bound pipeline in a thread to prevent blocking event loop
        result, truth = await anyio.to_thread.run_sync(run_pipeline, seed, partition, partition)
        metrics = await anyio.to_thread.run_sync(evaluate, result, truth)
        _RUNS[run_id]["result"] = result
        _RUNS[run_id]["metrics"] = metrics
        _RUNS[run_id]["status"] = "COMPLETE"
    except Exception as e:
        logger.exception(f"Pipeline run {run_id} failed for partition {partition}: {e}")
        _RUNS[run_id]["status"] = "FAILED"

@router.get("/reconcile/latest/results", response_model=RunScorecard)
async def get_latest_results(db=Depends(get_db)):
    if not _RUNS:
        return RunScorecard(
            run_id=uuid.uuid4(),
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
    # Get last run
    last_run_id = list(_RUNS.keys())[-1]
    return await get_results(last_run_id, db)

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
        value_covered_minor=metrics["verified_value_minor"] if metrics else 0,
        value_verified_minor=metrics["verified_value_minor"] if metrics else 0,
        unsafe_automation_pct=metrics["false_auto_match_rate"] if metrics else 0.0,
        review_burden_pct=result.review_rate,
        adversarial_holdout=None,
        ablation=None
    )

@router.post("/reconcile/replay", response_model=ReplayResponse)
async def replay_reconcile(request: ReplayRequest, db=Depends(get_db)):
    from app.schemas import ReplayDecisionDiff
    import copy
    
    run_data = _RUNS.get(request.run_id)
    if not run_data or run_data["status"] != "COMPLETE":
        # Cannot replay an incomplete or missing run
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Invalid or incomplete run_id")
        
    baseline_result = run_data["result"]
    partition = run_data["partition"]
    
    # 1. Re-derive source records
    from generator.config import GeneratorConfig, PARTITION_SEEDS
    from generator.events import EconomicEventGenerator
    from generator.views import SourceViewDeriver
    
    seed = PARTITION_SEEDS.get(partition, "razorledger-dev-v1")
    cfg = GeneratorConfig(seed=seed, partition=partition)
    events = EconomicEventGenerator(cfg).generate()
    deriver = SourceViewDeriver(cfg)
    raw_records, truth = deriver.derive(events)
    
    seen_sids = set()
    clean_records = []
    for rec in raw_records:
        r = copy.copy(rec)
        r.pop('ground_truth_group_id', None)
        key = (r['source'], r['source_event_id'])
        if key in seen_sids:
            continue
        seen_sids.add(key)
        sid = f"{r['source']}-{r['source_event_id']}"
        r.setdefault('source_record_id', sid)
        clean_records.append(r)
        
    # 2. Mock LLMEvidenceGenerator to prevent live API calls during replay
    from app.pipeline import ReconciliationPipeline, load_config
    import app.matching.llm
    
    class MockLLMEvidenceGeneratorReplay(app.matching.llm.LLMEvidenceGenerator):
        def should_invoke(self, ranked: list, index: int) -> bool:
            return False # Skip live LLM in replay

    # 3. Deep copy configuration
    replay_cfg = copy.deepcopy(load_config())
    baseline_cfg = load_config()
    
    baseline_am = baseline_cfg.get('matching', {}).get('auto_match_threshold', 0.80)
    baseline_rev = baseline_cfg.get('matching', {}).get('review_threshold', 0.40)
    
    if 'matching' not in replay_cfg:
        replay_cfg['matching'] = {}
    replay_cfg['matching']['auto_match_threshold'] = request.auto_match_threshold
    replay_cfg['matching']['review_threshold'] = request.review_threshold
    
    # 4. Run temporary pipeline
    from app.matching.evidence import compute_rarity_frequencies
    rarity = compute_rarity_frequencies(clean_records)
    
    pipeline = ReconciliationPipeline(config=replay_cfg, rarity_frequencies=rarity)
    pipeline.llm = MockLLMEvidenceGeneratorReplay(replay_cfg) # inject mock
    
    # Actually run the pipeline simulation
    replay_result = pipeline.run(clean_records, seed=seed)
    
    # 5. Compare baseline vs replay
    baseline_dec_map = {d.source_event_id: d for d in baseline_result.decisions}
    
    promoted = []
    demoted = []
    unchanged = []
    pending_changes = []
    no_match_changes = []
    
    for r_dec in replay_result.decisions:
        b_dec = baseline_dec_map.get(r_dec.source_event_id)
        if not b_dec: continue
        
        diff = ReplayDecisionDiff(
            source_record_id=r_dec.source_event_id,
            baseline_action=b_dec.action,
            replay_action=r_dec.action,
            baseline_confidence=b_dec.confidence,
            replay_confidence=r_dec.confidence,
            baseline_threshold=baseline_am,
            replay_threshold=request.auto_match_threshold,
            primary_reason=r_dec.primary_reason,
            control_result=r_dec.control_result,
            stage_f_status="REJECTED" if "FAIL" in r_dec.control_result else "PASSED"
        )
        
        if b_dec.action != r_dec.action:
            if b_dec.action == "REVIEW" and r_dec.action == "MATCH":
                promoted.append(diff)
            elif b_dec.action == "MATCH" and r_dec.action == "REVIEW":
                demoted.append(diff)
            elif r_dec.action == "PENDING":
                pending_changes.append(diff)
            elif r_dec.action == "NO_MATCH":
                no_match_changes.append(diff)
            else:
                demoted.append(diff) # catch-all
        else:
            unchanged.append(diff)
            
    b_scorecard = {
        "auto_resolved": baseline_result.auto_resolved,
        "review": baseline_result.review_count,
        "no_match": baseline_result.no_match_count,
        "pending": baseline_result.pending_count
    }
    r_scorecard = {
        "auto_resolved": replay_result.auto_resolved,
        "review": replay_result.review_count,
        "no_match": replay_result.no_match_count,
        "pending": replay_result.pending_count
    }
            
    return ReplayResponse(
        baseline_config={"auto_match_threshold": baseline_am, "review_threshold": baseline_rev},
        replay_config={"auto_match_threshold": request.auto_match_threshold, "review_threshold": request.review_threshold},
        baseline_scorecard=b_scorecard,
        replay_scorecard=r_scorecard,
        promoted=promoted,
        demoted=demoted,
        unchanged=unchanged,
        pending_changes=pending_changes,
        no_match_changes=no_match_changes
    )
