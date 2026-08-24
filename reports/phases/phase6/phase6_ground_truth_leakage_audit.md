# Phase 6 Ground-Truth Leakage Audit

**Status:** PASS
**Date:** 2026-08-24

## Objective
Trace the actual runtime path used for inference and prove that no ground-truth/evaluation-only information reaches the inference engines (blocking, scoring, allocator, controls, decision).

## Findings
1.  **Ingestion Barrier (`app/ingest.py`)**:
    During ingestion of JSON records, before any database `INSERT` operation, the code explicitly drops the ground truth labels:
    ```python
    for record in records:
        # 1. Pop ground_truth_group_id
        record.pop("ground_truth_group_id", None)
    ```
2.  **Database Schema**:
    The `source_records` table explicitly restricts inserted columns to: `run_id, source, source_event_id, amount_minor_units, currency, reference, counterparty, description, transaction_date, lifecycle_state, raw_payload`.
    No evaluation labels are stored.
3.  **Pipeline Inference (`app/pipeline.py`)**:
    The `ReconciliationPipeline` fetches candidate records strictly from the `source_records` table via SQLAlchemy. Because the labels were dropped at the ingestion barrier, the pipeline possesses absolutely no mechanism to read or act upon `ground_truth_group_id`.
4.  **Evaluator Separation (`app/evaluator.py`)**:
    Ground truth is joined back into the decisions *post-inference* by the `ReconciliationEvaluator` matching on `source_event_id` against the original dataset. The inference engines never interact with the evaluator.

## Conclusion
The system enforces a hard architectural boundary. No ground-truth leakage exists in candidate generation, scoring, or decision making. The audit is PASSED.
