import sys
import types

from app.matching.llm import GroqProvider, GeminiProvider
GroqProvider.generate = lambda self, p, s, max_attempts, run_id, batch_size: (False, "", 0, 0, 0.0, self.model)
GeminiProvider.generate = lambda self, p, s, max_attempts, run_id, batch_size: (False, "", 0, 0, 0.0, self.model)

import pytest
from evaluation.ablation import AblationEvaluator

def test_ablation_f_stage_safety():
    # Use ADVERSARIAL_HOLDOUT for explicit safety check
    evaluator = AblationEvaluator(seed='razorledger-adv-v1', partition='ADVERSARIAL_HOLDOUT')
    result = evaluator.run_ablation()
    
    f_stage = result['results_by_stage']['F']
    false_auto = f_stage.raw_metrics.get('false_auto_matches', 0)
    
    assert false_auto == 0, f"Safety violation! F stage had {false_auto} false auto-matches on Adversarial Holdout."
