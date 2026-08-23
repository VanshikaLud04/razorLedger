from fastapi import APIRouter, Depends
from app.schemas import ReviewQueueResponse, ReviewQueueItem, ReviewResolution, ReviewResolutionResponse, SourceRecordIn
import uuid

router = APIRouter()

def get_db():
    pass

@router.get("/review-queue", response_model=ReviewQueueResponse)
async def get_review_queue(db=Depends(get_db)):
    from app.routes.reconcile import _RUNS
    
    # Find the most recently completed run
    latest_run = None
    for run_id, data in _RUNS.items():
        if data["status"] == "COMPLETE":
            latest_run = data
            
    if not latest_run:
        return ReviewQueueResponse(items=[], total_open=0, total_value_at_risk_minor=0)
        
    result = latest_run["result"]
    items = []
    total_value = 0
    
    # Generate ReviewQueueItems for decisions with action == 'REVIEW'
    for dec in result.decisions:
        if dec.action == 'REVIEW':
            total_value += dec.amount_minor_units
            
            # Reconstruct the SourceRecordIn roughly for UI display
            # We don't have the original raw record stored perfectly here, but we have enough for UI demo
            src = SourceRecordIn(
                source=dec.source_event_id.split('-')[0] if '-' in dec.source_event_id else "BANK",
                source_event_id=dec.source_event_id,
                amount_minor_units=dec.amount_minor_units,
                currency="INR",
                transaction_date="2026-08-01", # mock date for UI
                lifecycle_state="CAPTURED",
                raw_payload={}
            )
            
            items.append(ReviewQueueItem(
                id=uuid.uuid4(),
                decision_id=uuid.uuid4(),
                source_record=src,
                candidates=[], # The UI can show this as empty for now, or we could pass the chosen_candidate
                primary_reason=dec.primary_reason or "MANUAL_REVIEW_REQUIRED",
                control_result=dec.control_result or "N/A",
                risk_exposure_score=1.0
            ))
            
    return ReviewQueueResponse(items=items, total_open=len(items), total_value_at_risk_minor=total_value)

@router.post("/review/{item_id}/resolve", response_model=ReviewResolutionResponse)
async def resolve_review(item_id: str, request: ReviewResolution, db=Depends(get_db)):
    return ReviewResolutionResponse(status="RESOLVED", audit_log_id=uuid.uuid4())
