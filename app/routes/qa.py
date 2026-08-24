import re
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from app.schemas import QARequest, QAResponse, QASource, QAFact
from app.routes.reconcile import _RUNS
from app.routes.review import _RESOLVED_ITEMS
from app.audit_chain import HashChainVerifier
from app.db import get_db
from fastapi import Depends
from sqlalchemy import text
from app.matching.llm import GroqProvider

logger = logging.getLogger(__name__)

router = APIRouter()

class QAExplanationSchema(BaseModel):
    explanation: str

def get_latest_run():
    latest_run = None
    for run_id, data in _RUNS.items():
        if data["status"] == "COMPLETE":
            latest_run = data
    return latest_run

def classify_question(q: str) -> str:
    q_low = q.lower()
    if any(k in q_low for k in ["audit", "hash", "verified", "chain"]):
        return "AUDIT"
    if any(k in q_low for k in ["how many", "percentage", "rate", "covered"]):
        if any(k in q_low for k in ["pending", "stale", "review", "open"]):
            return "PENDING_REVIEW"
        return "RUN_METRIC"
    if "control" in q_low or "blocked" in q_low or "ctrl-" in q_low or "stage f" in q_low:
        return "CONTROL_EXPLANATION"
    return "RECORD_EXPLANATION"

@router.post("/qa", response_model=QAResponse)
async def ask_qa(req: QARequest, db=Depends(get_db)):
    q_type = classify_question(req.question)
    
    facts = []
    sources = []
    
    run = None
    if req.run_id and req.run_id in _RUNS:
        run = _RUNS[req.run_id]
    else:
        run = get_latest_run()
        
    if not run and q_type != "AUDIT":
        return QAResponse(
            answer="No reconciliation run found.",
            grounding="INSUFFICIENT_DATA",
            question_type=q_type,
            sources=[],
            facts=[],
            llm_used=False
        )
        
    # Retrieval logic based on type
    if q_type == "AUDIT":
        if not req.entity_id:
            return QAResponse(
                answer="No entity ID provided for audit query.",
                grounding="INSUFFICIENT_DATA",
                question_type=q_type,
                sources=[],
                facts=[],
                llm_used=False
            )
        
        # Verify from DB
        is_verified = True
        entry_count = 0
        failure_reason = "Unknown"
        
        if db:
            query = text("""
                SELECT run_id, event_type, new_state, actor, created_at, previous_hash, current_hash,
                       old_state, primary_reason, control_result, action, matcher_version, prompt_version
                FROM audit_log WHERE entity_id = :entity_id ORDER BY created_at ASC
            """)
            result = await db.execute(query, {'entity_id': req.entity_id})
            rows = result.fetchall()
            
            entries = []
            for row in rows:
                run_id, event_type, new_state, actor, created_at, prev_hash, curr_hash, old_state, primary_reason, control_result, action, matcher_version, prompt_version = row
                created_at_iso = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
                
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
                    "entity_id": req.entity_id,
                    "decision_id": run_id,
                    "timestamp": created_at_iso,
                    "action": action,
                    "reason": primary_reason,
                    "metadata": metadata,
                    "previous_hash": prev_hash,
                    "current_hash": curr_hash
                })
            
            is_verified, broken_idx, failure_reason = HashChainVerifier.verify_chain(entries)
            entry_count = len(entries)
        
        facts.append(QAFact(label="Audit chain verified", value=str(is_verified)))
        facts.append(QAFact(label="Entry count", value=str(entry_count)))
        if not is_verified:
            facts.append(QAFact(label="Failure reason", value=failure_reason or "Unknown"))
        sources.append(QASource(type="audit", id=req.entity_id))

    elif q_type == "RUN_METRIC":
        result_obj = run["result"]
        metrics = result_obj.scorecard.model_dump() if hasattr(result_obj, "scorecard") else {}
        if not metrics:
            return QAResponse(
                answer="Scorecard not available.",
                grounding="INSUFFICIENT_DATA",
                question_type=q_type,
                sources=[],
                facts=[],
                llm_used=False
            )
        
        for k, v in metrics.items():
            if k in ["records_total", "auto_resolved", "review", "no_match", "pending", "value_covered_minor", "unsafe_automation_pct", "review_burden_pct"]:
                facts.append(QAFact(label=k, value=str(v)))
        sources.append(QASource(type="run", id=str(run.get("id", "latest"))))

    elif q_type == "PENDING_REVIEW":
        result_obj = run["result"]
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        created_at = run.get("created_at", now)
        age_seconds = max(0, int((now - created_at).total_seconds()))
        is_stale = age_seconds > 86400
        
        pending_count = 0
        review_count = 0
        stale_count = 0
        
        for dec in result_obj.decisions:
            if dec.action == "PENDING":
                pending_count += 1
            elif dec.action == "REVIEW":
                import uuid
                item_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, dec.source_event_id))
                if item_id not in _RESOLVED_ITEMS:
                    review_count += 1
                    if is_stale:
                        stale_count += 1
                        
        facts.append(QAFact(label="Pending records", value=str(pending_count)))
        facts.append(QAFact(label="Open reviews", value=str(review_count)))
        facts.append(QAFact(label="Stale reviews", value=str(stale_count)))
        sources.append(QASource(type="run", id="latest"))
        
    elif q_type in ["RECORD_EXPLANATION", "CONTROL_EXPLANATION"]:
        if not req.entity_id:
            return QAResponse(
                answer="No entity ID provided for record query.",
                grounding="INSUFFICIENT_DATA",
                question_type=q_type,
                sources=[],
                facts=[],
                llm_used=False
            )
        result_obj = run["result"]
        dec = next((d for d in result_obj.decisions if d.source_event_id == req.entity_id), None)
        if not dec:
            return QAResponse(
                answer=f"Entity {req.entity_id} not found in the latest run.",
                grounding="INSUFFICIENT_DATA",
                question_type=q_type,
                sources=[],
                facts=[],
                llm_used=False
            )
            
        # Provisional action vs final action isn't strictly saved differently in DecisionRecord right now,
        # but we can infer: if control_result is present and FAIL, provisional was MATCH.
        provisional = "MATCH" if dec.control_result and "FAIL" in dec.control_result else dec.action
            
        facts.append(QAFact(label="Provisional decision", value=provisional))
        facts.append(QAFact(label="Final decision", value=dec.action))
        
        if dec.primary_reason:
            facts.append(QAFact(label="Reason", value=dec.primary_reason))
        if dec.control_result and dec.control_result != "N/A":
            facts.append(QAFact(label="Control result", value=dec.control_result))
            
        sources.append(QASource(type="decision", id=req.entity_id))
        
        if "CTRL-" in (dec.control_result or ""):
            import re
            m = re.search(r'(CTRL-\d+)', dec.control_result)
            if m:
                sources.append(QASource(type="control", id=m.group(1)))
                
        if dec.action == "PENDING":
            facts.append(QAFact(label="Lifecycle state", value="Unsettled within window"))

    if not facts:
        return QAResponse(
            answer="No relevant facts could be retrieved.",
            grounding="INSUFFICIENT_DATA",
            question_type=q_type,
            sources=[],
            facts=[],
            llm_used=False
        )

    # Prompt LLM
    provider = GroqProvider()
    
    prompt = (
        "You are a read-only explanation assistant for RazorLedger.\n"
        "Answer the user's question concisely using ONLY the structured facts below.\n"
        "Do not invent facts, numbers, or statuses.\n"
        "Do not make financial recommendations.\n\n"
        f"FACTS:\n"
    )
    for f in facts:
        prompt += f"- {f.label}: {f.value}\n"
        
    prompt += f"\nQUESTION: {req.question}\n\n"
    prompt += (
        "Return a JSON object with exactly one key: 'explanation'.\n"
        "Provide a concise natural-language explanation based strictly on the facts."
    )
    
    success, llm_text, _, _, _, _ = provider.generate(
        prompt=prompt,
        schema_class=None,
        max_attempts=2,
        run_id="qa",
        batch_size=1
    )
    
    if not success:
        return QAResponse(
            answer="LLM explanation unavailable. Verified backend facts are still available.",
            grounding="PROVIDER_UNAVAILABLE",
            question_type=q_type,
            sources=sources,
            facts=facts,
            llm_used=False
        )
        
    try:
        try:
            data = json.loads(llm_text)
        except:
            # fallback if missing brackets
            start = llm_text.find('{')
            end = llm_text.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(llm_text[start:end+1])
            else:
                data = {}
        answer = data.get("explanation", "Could not parse explanation.")
    except Exception as e:
        answer = "Could not parse explanation."
        
    return QAResponse(
        answer=answer,
        grounding="GROUNDED",
        question_type=q_type,
        sources=sources,
        facts=facts,
        llm_used=True
    )
