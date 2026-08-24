# RazorLedger LLM Findings

**Date:** 2026-08-24
**Version:** 1.0.0 (Production Ready)

## Hypothesis
The original thesis postulated that a Large Language Model (Groq Llama3 / Gemini 1.5) could ingest JSON artifacts of fuzzy edge-cases, interpret unstructured human intent (e.g., memo strings like "tax offset" or "refund for 3 items"), and provide a numeric confidence boost that would push border-line matches over the `auto_match_threshold`.

## Findings

### 1. Actual Measured Lift
- **Non-zero deltas:** The LLM consistently applied non-zero delta scores (e.g. `+0.05` or `-0.02`) based on semantic matching of memo fields.
- **LLM-caused REVIEW -> MATCH transitions:** **0**.
- **Safe Automation Lift:** **0.0%**.

### 2. Why it Failed to Move the Needle
- **Safety Margin:** The `auto_match_threshold` is strictly set to 0.80. The maximum boost the LLM is allowed to provide is bounded (`+0.10`). For an LLM to elevate a match from REVIEW to MATCH, the base Evidence-Weighted Score (Stage D) had to be at least `0.70`.
- **The Threshold Gap:** In practice, matches scored between 0.70 and 0.79 were extremely rare. Matches usually fell into two categories:
  1. High-confidence deterministic/fuzzy matches (Base Score > 0.80).
  2. Very low-confidence garbage matches (Base Score < 0.40).
- Because there was almost no density of records in the `[0.70, 0.79]` band, the LLM had no candidates to meaningfully boost. The few that were boosted reached ~0.76, remaining in REVIEW.

### 3. API Reliability and Rate Limits
- Live API evaluations proved brittle. Rate limits (429s) and invalid key errors (401s) required extensive retry logic and fallback chaining (Groq -> Gemini).
- In a high-throughput financial environment, the latency overhead of calling an LLM (~2s per record) for a 0% lift is an unacceptable architectural tradeoff.

## Conclusion
The LLM integration is structurally sound and safely bounded. However, the empirical data proves that for standard financial reconciliation (which is largely structural and arithmetic rather than unstructured text-heavy), **an LLM is the wrong tool for the job**.

The dramatic 65%+ increase in automation was driven entirely by structural engineering (Evidence-Weighted Scoring and 1:N Graph Allocation), not Generative AI.
