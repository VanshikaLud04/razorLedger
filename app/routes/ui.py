from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@router.get("/reconciliation_run")
async def reconciliation_run(request: Request):
    return templates.TemplateResponse(request=request, name="reconciliation_run.html")

@router.get("/match_review_queue")
async def match_review_queue(request: Request):
    return templates.TemplateResponse(request=request, name="match_review_queue.html")

@router.get("/model_performance")
async def model_performance(request: Request):
    return templates.TemplateResponse(request=request, name="model_performance.html")

@router.get("/controls_and_safety")
async def controls_and_safety(request: Request):
    return templates.TemplateResponse(request=request, name="controls_and_safety.html")

@router.get("/allocation_visual")
async def allocation_visual(request: Request):
    return templates.TemplateResponse(request=request, name="allocation_visual.html")

@router.get("/decision_detail")
async def decision_detail(request: Request):
    return templates.TemplateResponse(request=request, name="decision_detail.html")
