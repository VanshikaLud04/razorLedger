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
            # Get last hash
            query = text("SELECT current_hash FROM audit_log WHERE entity_id = :entity_id ORDER BY created_at DESC LIMIT 1")
            # For synchronous SQLAlchemy or mock, we fetch (assuming async session here)
            result = await self.db_session.execute(query, {'entity_id': entity_id})
            row = result.fetchone()
            if row:
                previous_hash = row[0]
                
        canonical_event_string = f'{run_id}|{entity_id}|{event_type}|{new_state}|{actor}|{created_at_iso}'
        hash_input = previous_hash + canonical_event_string
        current_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest() if self.enabled_hash_chain else None

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
            
        query = text("SELECT run_id, event_type, new_state, actor, created_at, previous_hash, current_hash FROM audit_log WHERE entity_id = :entity_id ORDER BY created_at ASC")
        result = await self.db_session.execute(query, {'entity_id': entity_id})
        rows = result.fetchall()
        
        if not rows:
            return True, "No logs for entity"
            
        computed_prev = 'GENESIS'
        
        for row in rows:
            run_id, event_type, new_state, actor, created_at, prev_hash, curr_hash = row
            
            if prev_hash != computed_prev:
                return False, f"Broken chain: expected prev_hash {computed_prev}, got {prev_hash}"
                
            created_at_iso = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
            
            canonical_event_string = f'{run_id}|{entity_id}|{event_type}|{new_state}|{actor}|{created_at_iso}'
            expected_curr = hashlib.sha256((computed_prev + canonical_event_string).encode('utf-8')).hexdigest()
            
            if curr_hash != expected_curr:
                return False, f"Broken chain: expected curr_hash {expected_curr}, got {curr_hash}"
                
            computed_prev = curr_hash
            
        return True, "Chain verified"
