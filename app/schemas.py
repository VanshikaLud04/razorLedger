from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime

class SourceRecordIn(BaseModel):
    source: Literal["BANK", "INVOICE", "GATEWAY"]
    source_event_id: str
    amount_minor_units: int
    currency: str = Field(min_length=3, max_length=3)
    reference: Optional[str] = None
    counterparty: Optional[str] = None
    description: Optional[str] = None
    transaction_date: date
    lifecycle_state: Literal["INITIATED","CAPTURED","PARTIALLY_SETTLED","SETTLED","REFUNDED","REVERSED","FAILED"]
    raw_payload: Dict[str, Any]
    ground_truth_group_id: Optional[str] = None

class IngestRequest(BaseModel):
    run_id: UUID
    records: List[SourceRecordIn]

class IngestResponse(BaseModel):
    accepted: int
    deduplicated: int
    rejected: int
    rejected_reasons: List[str]

class ReconcileRunRequest(BaseModel):
    dataset_seed: str
    dataset_partition: Literal["DEV","VALIDATION","ADVERSARIAL_HOLDOUT","FROZEN_UNSEEN"]
    thresholds: Dict[str, Any]
    embedding_model: str
    llm_model: str
    prompt_version: str

class ReconcileRunResponse(BaseModel):
    run_id: UUID
    status: Literal["RUNNING","COMPLETE","FAILED"]

class RunScorecard(BaseModel):
    run_id: UUID
    records_total: int
    auto_resolved: int
    review: int
    no_match: int
    pending: int
    value_covered_minor: int
    value_verified_minor: int
    unsafe_automation_pct: float
    review_burden_pct: float
    adversarial_holdout: Optional[Dict[str, Any]] = None
    ablation: Optional[Dict[str, Any]] = None

class ReviewQueueItem(BaseModel):
    id: UUID
    decision_id: UUID
    source_record: SourceRecordIn
    candidates: List[Dict[str, Any]]
    primary_reason: str
    control_result: str
    risk_exposure_score: Optional[float] = None

class ReviewQueueResponse(BaseModel):
    items: List[ReviewQueueItem]
    total_open: int
    total_value_at_risk_minor: int

class ReviewResolution(BaseModel):
    resolved_candidate_id: Optional[UUID] = None
    resolver: str

class ReviewResolutionResponse(BaseModel):
    status: Literal["RESOLVED"]
    audit_log_id: UUID

class AuditEntry(BaseModel):
    id: UUID
    event_type: str
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    primary_reason: Optional[str] = None
    control_result: Optional[str] = None
    action: Optional[str] = None
    actor: str
    created_at: datetime
    current_hash: str

class AuditTrailResponse(BaseModel):
    entity_id: UUID
    chain_verified: bool
    entries: List[AuditEntry]

class JournalApprovalRequest(BaseModel):
    economic_event_id: UUID
    approver: str

class JournalApprovalResponse(BaseModel):
    status: Literal["APPROVED"]
    proposed_entry: Dict[str, Any]
