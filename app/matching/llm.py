import os
import json
import logging
import time
import re
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# --- PYDANTIC SCHEMAS ---

class LLMAssessment(BaseModel):
    group_id: str
    cand1_supporting_evidence: str
    cand1_contradicting_evidence: str
    cand2_supporting_evidence: str
    cand2_contradicting_evidence: str
    comparative_preference: Literal[
        'CANDIDATE_1_STRONGLY_PREFERRED',
        'CANDIDATE_1_MILDLY_PREFERRED',
        'NO_CLEAR_PREFERENCE',
        'CANDIDATE_2_MILDLY_PREFERRED',
        'CANDIDATE_2_STRONGLY_PREFERRED'
    ]
    uncertainty_level: Literal['LOW', 'MEDIUM', 'HIGH']

class BatchLLMAssessment(BaseModel):
    assessments: List[LLMAssessment]

# --- PROVIDER ---

class GroqProvider:
    def __init__(self, model_name: str = "qwen/qwen3.6-27b", api_key: str | None = None):
        import groq as groq_lib
        self.client = groq_lib.Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"), timeout=30.0)
        self.model = model_name

    def generate(self, prompt: str, schema_class, max_attempts: int, run_id: str, batch_size: int):
        in_t = out_t = 0
        cost = 0.0
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1200,
                    temperature=0.0,
                    extra_body={"reasoning_effort": "none"}
                )
                
                usage = resp.usage
                in_t += usage.prompt_tokens
                out_t += usage.completion_tokens
                cost += (usage.prompt_tokens / 1_000_000) * 0.05 + (usage.completion_tokens / 1_000_000) * 0.15
                
                content = resp.choices[0].message.content.strip()
                
                # strip out reasoning/think blocks if they leaked
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                if content.startswith('\x60\x60\x60'):
                    content = re.sub(r'^\x60\x60\x60(json)?', '', content)
                    content = re.sub(r'\x60\x60\x60$', '', content).strip()
                
                # try finding JSON bracket
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    content = content[start:end+1]
                
                return True, content, in_t, out_t, cost, self.model
            except Exception as e:
                logger.warning(f"Groq API error on attempt {attempt}: {e}")
                time.sleep(1)
                
        return False, "", in_t, out_t, cost, self.model


# --- PIPELINE ADAPTER ---

class LLMEvidenceGenerator:
    def __init__(self, config: dict):
        self.config = config
        self.exact_ties = 0
        self.passed_gate = 0
        self.queued = 0
        self.groups_sent = 0
        self.groups_assessed = 0
        self.groups_failed = 0
        self.calls_used = 0
        self.max_groups_per_call = 2
        self.total_cost = 0.0
        self.in_tokens = 0
        self.out_tokens = 0
        
        self.provider = GroqProvider(model_name="qwen/qwen3.6-27b")

    def should_invoke(self, ranked: list, index: int) -> bool:
        self.exact_ties += 1
        conf = ranked[index].get('probabilistic_confidence', 0.0)
        gap = ranked[index].get('confidence_gap_to_next', 1.0)
        if conf >= 0.60 and gap < 0.10:
            self.passed_gate += 1
            if self.queued < 70:
                self.queued += 1
                return True
        return False

    def generate_batch(self, batch_prompts: list, run_id: str) -> list:
        if not batch_prompts:
            return []
            
        self.groups_sent += len(batch_prompts)
        self.calls_used += 1
        
        serialized_batch = []
        for p in batch_prompts:
            src_raw = p.get('source_record', {})
            cands = p.get('top_candidates', [])
            cand1_raw = cands[0].get('record', {}) if len(cands) > 0 else {}
            cand2_raw = cands[1].get('record', {}) if len(cands) > 1 else {}
            
            def extract(r):
                if not r: return {}
                return {
                    "id": r.get("source_record_id"),
                    "src": r.get("source"),
                    "amt": r.get("amount_minor_units"),
                    "ref": r.get("reference"),
                    "pty": r.get("counterparty"),
                    "dt": str(r.get("transaction_date")) if r.get("transaction_date") else None,
                    "desc": r.get("description")
                }
            
            serialized_batch.append({
                "group_id": src_raw.get('source_record_id', 'UNK'),
                "source": extract(src_raw),
                "cand1": extract(cand1_raw),
                "cand2": extract(cand2_raw)
            })
            
        prompt = (
            "Compare candidates holistically against the source record for each group in this batch. "
            "Do not invent facts. Return supporting/contradicting evidence for each candidate. "
            "Return ONLY one JSON object. No markdown. No explanation. "
            "Do not use '...', placeholders, or omitted fields. "
            "Evidence fields must contain concrete evidence from the supplied records. If there is no evidence, explicitly state 'No contradicting evidence found.' "
            "Do not make final MATCH/REVIEW decisions.\n\n"
            f"BATCH DATA:\n{json.dumps(serialized_batch, default=str)}\n\n"
            'The JSON must have this exact structure:\n'
            '{"assessments": [\n'
            '  {\n'
            '    "group_id": "<string>",\n'
            '    "cand1_supporting_evidence": "<string>",\n'
            '    "cand1_contradicting_evidence": "<string>",\n'
            '    "cand2_supporting_evidence": "<string>",\n'
            '    "cand2_contradicting_evidence": "<string>",\n'
            '    "comparative_preference": "<must be one of: CANDIDATE_1_STRONGLY_PREFERRED, CANDIDATE_1_MILDLY_PREFERRED, NO_CLEAR_PREFERENCE, CANDIDATE_2_MILDLY_PREFERRED, CANDIDATE_2_STRONGLY_PREFERRED>",\n'
            '    "uncertainty_level": "<must be one of: LOW, MEDIUM, HIGH>"\n'
            '  }\n'
            ']}\n'
        )
            
        success, text, in_t, out_t, cost, model = self.provider.generate(
            prompt, BatchLLMAssessment, max_attempts=3, run_id=run_id, batch_size=len(batch_prompts)
        )
        self.total_cost += cost
        self.in_tokens += in_t
        self.out_tokens += out_t
        
        results = []
        parsed = None
        if success:
            try:
                try:
                    raw_data = json.loads(text)
                except:
                    raw_data = {}
                
                if isinstance(raw_data, list):
                    raw_data = {"assessments": raw_data}
                elif isinstance(raw_data, dict) and "assessments" not in raw_data:
                    raw_data = {"assessments": [raw_data]}
                    
                parsed = BatchLLMAssessment(**raw_data)
                
                # build dict by group
                parsed_map = {a.group_id: a for a in parsed.assessments}
                for p in batch_prompts:
                    gid = p.get('source_record', {}).get('source_record_id', 'UNK')
                    if gid in parsed_map:
                        results.append(parsed_map[gid])
                        self.groups_assessed += 1
                    else:
                        # FAIL -> REVIEW
                        results.append(LLMAssessment(
                            group_id=gid,
                            cand1_supporting_evidence="FAIL", cand1_contradicting_evidence="FAIL",
                            cand2_supporting_evidence="FAIL", cand2_contradicting_evidence="FAIL",
                            comparative_preference="NO_CLEAR_PREFERENCE", uncertainty_level="HIGH"
                        ))
                        self.groups_failed += 1
            except ValidationError as e:
                logger.error(f"Pydantic error: {e}")
                parsed = None
                
        if not parsed:
            for p in batch_prompts:
                self.groups_failed += 1
                results.append(LLMAssessment(
                    group_id=p.get('source_record', {}).get('source_record_id', 'UNK'),
                    cand1_supporting_evidence="FAIL", cand1_contradicting_evidence="FAIL",
                    cand2_supporting_evidence="FAIL", cand2_contradicting_evidence="FAIL",
                    comparative_preference="NO_CLEAR_PREFERENCE", uncertainty_level="HIGH"
                ))
                
        return results
