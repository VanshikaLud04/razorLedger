# RazorLedger

**Status:** Final Freeze (Phase 7)
**Primary Architecture:** `OneToNAllocator` + `FinancialControlEngine`
**Safe Automation Rate:** 80.2% (DEV) | 84.7% (FROZEN_UNSEEN)
**False Auto-Match Rate:** 0.0%

## Problem
Financial reconciliation is typically trapped between two extremes:
1. Hardcoded, deterministic string matching (safe, but maxes out at ~15% automation).
2. Generative AI or machine learning models (higher automation, but prone to hallucinations and non-deterministic financial errors).

## Thesis
RazorLedger was built to test if we could achieve ML-like automation rates using structural data engineering (Evidence-Weighted Scoring and Graph Allocation) while guaranteeing the 100% precision of deterministic systems through an independent `FinancialControlEngine`.

## Architecture (Stages A-F)
The final locked pipeline architecture is as follows:
- **Stages A-C (Candidate Discovery):** Deterministic, Fuzzy, and Semantic matchers gather candidate edges between Ledgers, Banks, and Gateways.
- **Stage D (Evidence-Weighted Scoring):** Matches are scored purely based on the mathematical rarity of the evidence (e.g. matching a rare Invoice ID is worth more than matching the word "Payment").
- **Stage E2 (OneToN Allocator):** Legitimate 1:N payment relationships are resolved structurally. The allocator groups candidates into strictly verified bipartite components.
- **Stage F (Financial Control Engine):** The absolute final authority. Before any candidate is elevated to `MATCH`, it is subjected to rigid invariants (e.g., `CTRL-001` Conservation of Value, `CTRL-002` Currency Lock). If it fails, it drops to `REVIEW`.

## Final Metrics (Phase 7)
*Compared against the Phase 1 deterministic baseline on the DEV partition.*

- **MATCH Count:** 68 ➔ 361 (+293)
- **Safe Automation:** 15.1% ➔ 80.2% (+65.1%)
- **Value Coverage:** 14.2% ➔ 81.5% (+67.3%)
- **Precision:** 100% ➔ 100%
- **False Auto-Match:** 0.0% ➔ 0.0%

### Adversarial and Unseen Results
The pipeline maintained 100% precision on the `TEST_ADVERSARIAL` partition (which contained simulated hallucination traps and tax mismatches) and generalized exceptionally well to the `FROZEN_UNSEEN` partition (achieving 84.7% safe automation without any tuning).

## LLM Findings
During Phase 3, we integrated a bounded LLM into Stage E to determine if Generative AI could safely boost automation. The empirical result: **0.0% safe automation lift**. The LLM could not mathematically surpass the 0.80 safety threshold for borderline cases without hallucinating. The massive 65%+ increase in automation was driven entirely by structural engineering (Evidence-Weighted Scoring and 1:N Graph Allocation).

## Reproducibility
The project contains exactly two canonical reproduction scripts in the `scripts/` directory:
1. `run_final_benchmark.py`: Runs the pipeline across all partitions.
2. `run_final_ablation.py`: Runs A-F feature ablation.

For full execution details, see `docs/final/FINAL_REPRODUCIBILITY.md`.

## Auditability
RazorLedger guarantees that:
- `FinancialControlEngine` cannot be bypassed.
- 0% Ground Truth Leakage exists.
- Every source record is disposed deterministically (MATCH, REVIEW, PENDING, NO_MATCH).
- Duplicate and over-allocations are structurally blocked.

For the detailed audit, see `docs/final/FINAL_SAFETY_AUDIT.md`.

## Known Limitations
- The system explicitly handles 1:1 and 1:N relationships. Complex M:N relationships (where multiple bank settlements cover multiple disjoint invoices simultaneously without clear intermediate routing) are structurally rejected to `REVIEW`.
