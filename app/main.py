from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routes.ingest import router as ingest_router
from app.routes.reconcile import router as reconcile_router
from app.routes.review import router as review_router
from app.routes.audit_trail import router as audit_router
from app.routes.approve import router as approve_router

load_dotenv()

app = FastAPI(title="RazorLedger — Verified Financial Reconciliation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow Stitch preview and local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(reconcile_router)
app.include_router(review_router)
app.include_router(audit_router)
app.include_router(approve_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
