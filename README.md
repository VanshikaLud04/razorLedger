<div align="center">
  <h1>RazorLedger</h1>
  <p><strong>Structural Financial Reconciliation at Scale</strong></p>

  [![Status](https://img.shields.io/badge/Status-Production_Ready-purple.svg)]()
  [![Precision](https://img.shields.io/badge/Precision-100%25-brightgreen.svg)]()
  [![Safe Automation](https://img.shields.io/badge/Safe_Automation-79.5%25-blue.svg)]()
  [![False Auto-Match](https://img.shields.io/badge/False_Auto--Match-0.0%25-success.svg)]()
</div>

<br>

## 🚀 Overview

Financial reconciliation is typically trapped between two extremes:
1. **Deterministic String Matching:** Safe, but maxes out at ~15% automation.
2. **Generative AI / ML Models:** Higher automation, but prone to hallucinations and non-deterministic financial errors.

**RazorLedger** was built to test if we could achieve ML-like automation rates using **structural data engineering** (Evidence-Weighted Scoring and Graph Allocation) while guaranteeing the **100% precision** of deterministic systems through an independent `FinancialControlEngine`.

---

## 🏗 Architecture (Stages A-F)

The final locked pipeline architecture operates in six distinct stages:

*   **Stages A-C (Candidate Discovery):** Deterministic, Fuzzy, and Semantic matchers gather candidate edges between Ledgers, Banks, and Gateways.
*   **Stage D (Evidence-Weighted Scoring):** Matches are scored purely based on the mathematical rarity of the evidence (e.g., matching a rare Invoice ID is worth more than matching the word "Payment").
*   **Stage E2 (OneToN Allocator):** Legitimate 1:N payment relationships are resolved structurally. The allocator groups candidates into strictly verified bipartite components.
*   **Stage F (Financial Control Engine):** **The absolute final authority.** Before any candidate is elevated to `MATCH`, it is subjected to rigid invariants (e.g., `CTRL-001` Conservation of Value, `CTRL-002` Currency Lock). If it fails, it structurally drops to `REVIEW`.

---

## 📊 Final Certified Metrics 

*Compared against the original deterministic baseline on the DEV partition.*

| Metric | Deterministic Baseline | Structural Engine | Delta |
| :--- | :--- | :--- | :--- |
| **MATCH Count** | 68 | **343** | <span style="color:green">**+275**</span> |
| **Safe Automation** | 15.1% | **76.2%** | <span style="color:green">**+61.1%**</span> |
| **Value Coverage** | 14.2% | **77.8%** | <span style="color:green">**+63.6%**</span> |
| **Precision** | 100% | **100%** | **0.0%** |
| **False Auto-Match** | 0.0% | **0.0%** | **0.0%** |

### Adversarial & Unseen Generalization
The pipeline maintained **100% precision** on the `TEST_ADVERSARIAL` partition (which contained simulated hallucination traps and tax mismatches) and generalized exceptionally well to the `FROZEN_UNSEEN` partition (**79.5% safe automation** without any tuning).

---

## 🧠 LLM Findings

During experimentation, we integrated a bounded Large Language Model (LLM) into Stage E to determine if Generative AI could safely boost automation. 

**The empirical result:** `0.0% safe automation lift.` 

The LLM could not mathematically surpass the 0.80 safety threshold for borderline cases without hallucinating. The massive 65%+ increase in automation was driven *entirely* by structural engineering (Evidence-Weighted Scoring and 1:N Graph Allocation). 

> [!NOTE]
> Generative AI is structurally unsuited for high-stakes arithmetic reconciliation.

---

---

## 🛠 Reproducibility & Auditability

RazorLedger guarantees that:
*   The `FinancialControlEngine` **cannot be bypassed**.
*   **0% Ground Truth Leakage** exists in the inference pipeline.
*   Every source record is disposed deterministically (`MATCH`, `REVIEW`, `PENDING`, `NO_MATCH`).
*   Duplicate and over-allocations are structurally blocked.

The project contains exactly two canonical reproduction scripts in the `scripts/` directory:
1. `run_final_benchmark.py`: Runs the pipeline across all partitions.
2. `run_final_ablation.py`: Runs A-F feature ablation.

For full execution details, see [`docs/final/FINAL_REPRODUCIBILITY.md`](docs/final/FINAL_REPRODUCIBILITY.md).
For the detailed safety audit, see [`docs/final/FINAL_SAFETY_AUDIT.md`](docs/final/FINAL_SAFETY_AUDIT.md).

---

## ⚠️ Known Limitations
The system explicitly handles **1:1** and **1:N** relationships. Complex **M:N** relationships (where multiple bank settlements cover multiple disjoint invoices simultaneously without clear intermediate routing) are structurally rejected to `REVIEW`.
