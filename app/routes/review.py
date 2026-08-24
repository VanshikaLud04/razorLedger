from fastapi import APIRouter, Depends
from app.schemas import ReviewQueueResponse, ReviewQueueItem, ReviewResolution, ReviewResolutionResponse, SourceRecordIn
import uuid

router = APIRouter()

def get_db():
    pass

from datetime import datetime, timezone

_RESOLVED_ITEMS = set()

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
    created_at = latest_run.get("created_at", datetime.now(timezone.utc))
    
    now = datetime.now(timezone.utc)
    age_seconds = int((now - created_at).total_seconds())
    if age_seconds < 0:
        age_seconds = 0
        
    age_hours = round(age_seconds / 3600.0, 1)
    is_stale = age_seconds > (24 * 60 * 60)
    
    if age_hours < 1.0:
        age_label = f"{age_seconds // 60}m"
    elif age_hours < 24.0:
        age_label = f"{int(age_hours)}h"
    else:
        age_label = f"{int(age_hours // 24)}d {int(age_hours % 24)}h"
        
    items = []
    total_value = 0
    
    # Generate ReviewQueueItems for decisions with action == 'REVIEW'
    for dec in result.decisions:
        if dec.action == 'REVIEW':
            item_id = uuid.uuid5(uuid.NAMESPACE_DNS, dec.source_event_id)
            if str(item_id) in _RESOLVED_ITEMS:
                continue
                
            total_value += dec.amount_minor_units
            
            src = SourceRecordIn(
                source=dec.source_event_id.split('-')[0] if '-' in dec.source_event_id else "BANK",
                source_event_id=dec.source_event_id,
                amount_minor_units=dec.amount_minor_units,
                currency="INR",
                transaction_date="2026-08-01", # mock date for UI
                lifecycle_state="CAPTURED",
                raw_payload={}
            )
            
            from app.schemas import ProposedJournalEntry, JournalLine
            
            proposed_journal = ProposedJournalEntry(
                lines=[
                    JournalLine(
                        type="DEBIT",
                        account="MANUAL ACCOUNT SELECTION REQUIRED",
                        amount_minor_units=dec.amount_minor_units,
                        currency="INR"
                    ),
                    JournalLine(
                        type="CREDIT",
                        account="MANUAL ACCOUNT SELECTION REQUIRED",
                        amount_minor_units=dec.amount_minor_units,
                        currency="INR"
                    )
                ],
                reason="Unresolved reconciliation mismatch requiring manual ledger allocation.",
                supporting_evidence=f"Source record {dec.source_event_id} ({src.source})"
            )
            
            items.append(ReviewQueueItem(
                id=item_id,
                decision_id=uuid.uuid5(uuid.NAMESPACE_DNS, "dec_" + dec.source_event_id),
                source_record=src,
                candidates=[], 
                primary_reason=dec.primary_reason or "MANUAL_REVIEW_REQUIRED",
                control_result=dec.control_result or "N/A",
                risk_exposure_score=1.0,
                created_at=created_at,
                age_seconds=age_seconds,
                age_hours=age_hours,
                age_label=age_label,
                is_stale=is_stale,
                proposed_journal=proposed_journal
            ))
            
    return ReviewQueueResponse(items=items, total_open=len(items), total_value_at_risk_minor=total_value)

@router.post("/review/{item_id}/resolve", response_model=ReviewResolutionResponse)
async def resolve_review(item_id: str, request: ReviewResolution, db=Depends(get_db)):
    _RESOLVED_ITEMS.add(item_id)
    return ReviewResolutionResponse(status="RESOLVED", audit_log_id=uuid.uuid4())
