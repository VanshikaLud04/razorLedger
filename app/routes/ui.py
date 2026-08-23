from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/reconciliation_run")
async def reconciliation_run(request: Request):
    return templates.TemplateResponse("reconciliation_run.html", {"request": request})

@router.get("/match_review_queue")
async def match_review_queue(request: Request):
    return templates.TemplateResponse("match_review_queue.html", {"request": request})

@router.get("/model_performance")
async def model_performance(request: Request):
    return templates.TemplateResponse("model_performance.html", {"request": request})

@router.get("/controls_and_safety")
async def controls_and_safety(request: Request):
    return templates.TemplateResponse("controls_and_safety.html", {"request": request})
