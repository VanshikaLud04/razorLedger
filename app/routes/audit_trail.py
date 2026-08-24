from fastapi import APIRouter, Depends
from app.schemas import AuditTrailResponse
import uuid

router = APIRouter()

def get_db():
    pass

from sqlalchemy import text
from app.audit_chain import HashChainVerifier
from app.schemas import AuditVerification, AuditEntry
from datetime import datetime

@router.get("/audit-trail/{entity_id}", response_model=AuditTrailResponse)
async def get_audit_trail(entity_id: str, db=Depends(get_db)):
    if db is None:
        return AuditTrailResponse(
            entity_id=uuid.UUID(entity_id), 
            chain_verified=True, 
            entries=[],
            verification=AuditVerification(
                algorithm="SHA-256",
                entry_count=0,
                first_broken_index=None,
                failure_reason=None
            )
        )
        
    query = text("""
        SELECT id, run_id, event_type, new_state, actor, created_at, previous_hash, current_hash,
               old_state, primary_reason, control_result, action, matcher_version, prompt_version
        FROM audit_log WHERE entity_id = :entity_id ORDER BY created_at ASC
    """)
    result = await db.execute(query, {'entity_id': entity_id})
    rows = result.fetchall()
    
    entries = []
    api_entries = []
    for row in rows:
        record_id, run_id, event_type, new_state, actor, created_at, prev_hash, curr_hash, old_state, primary_reason, control_result, action, matcher_version, prompt_version = row
        created_at_iso = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
        
        metadata = {
            "event_type": event_type,
            "old_state": old_state,
            "new_state": new_state,
            "control_result": control_result,
            "actor": actor,
            "matcher_version": matcher_version,
            "prompt_version": prompt_version
        }
        
        entries.append({
            "entity_id": entity_id,
            "decision_id": run_id,
            "timestamp": created_at_iso,
            "action": action,
            "reason": primary_reason,
            "metadata": metadata,
            "previous_hash": prev_hash,
            "current_hash": curr_hash
        })
        
        api_entries.append(AuditEntry(
            id=record_id,
            event_type=event_type,
            old_state=old_state,
            new_state=new_state,
            primary_reason=primary_reason,
            control_result=control_result,
            action=action,
            actor=actor,
            created_at=created_at,
            current_hash=curr_hash
        ))
        
    is_verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
    
    return AuditTrailResponse(
        entity_id=uuid.UUID(entity_id),
        chain_verified=is_verified,
        entries=api_entries,
        verification=AuditVerification(
            algorithm="SHA-256",
            entry_count=len(entries),
            first_broken_index=broken_idx,
            failure_reason=failure_reason
        )
    )
