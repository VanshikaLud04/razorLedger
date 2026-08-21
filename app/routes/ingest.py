from fastapi import APIRouter, Depends
from app.schemas import IngestRequest, IngestResponse
from app.ingest import IngestService

def get_db():
    # Mock DB dependency for FastAPI
    pass

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse)
async def ingest_route(request: IngestRequest, db=Depends(get_db)):
    service = IngestService(db, str(request.run_id))
    # converting records to dict
    records = [r.dict() for r in request.records]
    res = await service.ingest(records)
    return IngestResponse(**res)
