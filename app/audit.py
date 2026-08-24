import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import text

class AuditLogger:
    def __init__(self, db_session, enabled_hash_chain: bool = True):
        self.db_session = db_session
        self.enabled_hash_chain = enabled_hash_chain

    async def log(
        self,
        run_id: str,
        entity_id: str,
        event_type: str,
        old_state: str | None,
        new_state: str | None,
        primary_reason: str | None,
        control_result: str | None,
        action: str | None,
        actor: str,
        matcher_version: str | None = None,
        prompt_version: str | None = None,
    ) -> dict:
        
        created_at_iso = datetime.now(timezone.utc).isoformat()
        previous_hash = 'GENESIS'
        
        if self.enabled_hash_chain:
            query = text("SELECT current_hash FROM audit_log WHERE entity_id = :entity_id ORDER BY created_at DESC LIMIT 1")
            result = await self.db_session.execute(query, {'entity_id': entity_id})
            row = result.fetchone()
            if row:
                previous_hash = row[0]
                
        metadata = {
            "event_type": event_type,
            "old_state": old_state,
            "new_state": new_state,
            "control_result": control_result,
            "actor": actor,
            "matcher_version": matcher_version,
            "prompt_version": prompt_version
        }
        
        from app.audit_chain import HashChainVerifier
        current_hash = HashChainVerifier.generate_hash(
            entity_id=entity_id,
            decision_id=run_id,
            timestamp=created_at_iso,
            action=action,
            reason=primary_reason,
            metadata=metadata,
            previous_hash=previous_hash
        ) if self.enabled_hash_chain else None

        insert_query = text("""
            INSERT INTO audit_log (
                run_id, entity_id, event_type, old_state, new_state, 
                primary_reason, control_result, action, actor, 
                matcher_version, prompt_version, previous_hash, current_hash, created_at
            ) VALUES (
                :run_id, :entity_id, :event_type, :old_state, :new_state,
                :primary_reason, :control_result, :action, :actor,
                :matcher_version, :prompt_version, :previous_hash, :current_hash, :created_at
            ) RETURNING id
        """)
        
        await self.db_session.execute(insert_query, {
            'run_id': run_id,
            'entity_id': entity_id,
            'event_type': event_type,
            'old_state': old_state,
            'new_state': new_state,
            'primary_reason': primary_reason,
            'control_result': control_result,
            'action': action,
            'actor': actor,
            'matcher_version': matcher_version,
            'prompt_version': prompt_version,
            'previous_hash': previous_hash,
            'current_hash': current_hash,
            'created_at': created_at_iso
        })
        
        return {
            'run_id': run_id,
            'entity_id': entity_id,
            'event_type': event_type,
            'old_state': old_state,
            'new_state': new_state,
            'actor': actor,
            'current_hash': current_hash,
            'previous_hash': previous_hash,
            'created_at': created_at_iso
        }

    async def verify_chain(self, entity_id: str) -> tuple[bool, str]:
        if not self.enabled_hash_chain:
            return True, "Hash chain disabled"
            
        query = text("""
            SELECT run_id, event_type, new_state, actor, created_at, previous_hash, current_hash,
                   old_state, primary_reason, control_result, action, matcher_version, prompt_version
            FROM audit_log WHERE entity_id = :entity_id ORDER BY created_at ASC
        """)
        result = await self.db_session.execute(query, {'entity_id': entity_id})
        rows = result.fetchall()
        
        if not rows:
            return True, "No logs for entity"
            
        from app.audit_chain import HashChainVerifier
        entries = []
        for row in rows:
            run_id, event_type, new_state, actor, created_at, prev_hash, curr_hash, old_state, primary_reason, control_result, action, matcher_version, prompt_version = row
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
            
        is_verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
        if not is_verified:
            return False, f"Broken chain at index {broken_idx}: {failure_reason}"
            
        return True, "Chain verified"
