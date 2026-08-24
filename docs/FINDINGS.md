# RazorLedger: P1 Findings & Evaluation Results

This document summarizes the results and findings of the P1 deterministic evaluation of RazorLedger's financial reconciliation engine.

## Overview
RazorLedger was evaluated across four strict, non-overlapping partitions of a 150-event synthetic dataset:
1. **DEV**: Iteration and threshold fitting.
2. **VALIDATION**: Held-out threshold tuning.
3. **ADVERSARIAL_HOLDOUT**: Heavily corrupted data and missing fields designed to stress the financial controls.
4. **FROZEN_UNSEEN**: The final, completely blind evaluation to benchmark true pipeline performance.

## Pipeline Architecture
The pipeline employs a layered architecture:
- **Deterministic and Fuzzy Matching** (RapidFuzz)
- **Semantic Evidence** (BGE-Small on descriptions)
- **Probabilistic Scoring** (Fellegi-Sunter)
- **LLM Evidence Verification** (Qwen 3.6 27B)
- **Financial Controls (Stage F)**: Absolute deterministic rules that intercept unsafe matches.

## Core Metrics (FROZEN_UNSEEN)
The final run yielded the following definitive metrics:
- **Safe Automation Rate**: `15.3%`
- **False Auto-Match Rate**: `0.0%` (Zero financial violations)
- **Review Burden**: High, but bounded. The remaining records were safely routed to `REVIEW` for human operators.
- **Unsafe Intercepts**: `89` (The Stage F controls successfully blocked 89 matches that were heuristically plausible but financially invalid).

## Key Discoveries
1. **Stage F Controls are the Anchor**: The system achieved 0.0% false auto-match rate purely because the independent Financial Controls (CTRL-001 through CTRL-010) enforce hard accounting boundaries (currency match, value conservation, positive balance).
2. **LLM Limitations and Strengths**: The LLM proved to be highly useful for semantic mapping of corrupted fields (e.g. mapping "Sub Pmt" to "Subscription Payment"). However, when presented with completely obfuscated data, it correctly abstained rather than hallucinating matches. 
3. **Threshold Calibration**: A conservative `auto_match_threshold` ensures that we heavily favor human review (`REVIEW` status) over probabilistic financial settlement.

## Operator Tools (P2 Extensions)
To address the high review burden resulting from strict controls, the following operator tools were added:
- **Cryptographic Hash-Chained Audit Trail**: Ensure decisions are tamper-evident.
- **Ledger Q&A**: Let operators query the LLM for explanations of pipeline blocking decisions.
- **Threshold Replay**: Simulate looser thresholds without impacting the active ledger.
