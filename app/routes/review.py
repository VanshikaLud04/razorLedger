from fastapi import APIRouter, Depends
from app.schemas import ReviewQueueResponse, ReviewResolution, ReviewResolutionResponse
import uuid

router = APIRouter()

def get_db():
    pass

@router.get("/review-queue", response_model=ReviewQueueResponse)
async def get_review_queue(db=Depends(get_db)):
    # Return all OPEN items from review_queue with their decisions + top candidates
    return ReviewQueueResponse(items=[], total_open=0, total_value_at_risk_minor=0)

@router.post("/review/{item_id}/resolve", response_model=ReviewResolutionResponse)
async def resolve_review(item_id: str, request: ReviewResolution, db=Depends(get_db)):
    # Update review_queue status=RESOLVED, write audit_log entry
    return ReviewResolutionResponse(status="RESOLVED", audit_log_id=uuid.uuid4())
