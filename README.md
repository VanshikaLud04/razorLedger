# RazorLedger — Verified Financial Reconciliation

> *"We didn't build a system that tries to reconcile everything. We built one that knows what it can safely reconcile."*

A multi-source financial reconciliation engine with deterministic financial controls, probabilistic evidence scoring, and an honest exception list.

**UI Preview (Stitch):** [RazorLedger Frontend Prototype](https://stitch.withgoogle.com/preview/5628332109741508169?node-id=efa091db75d944e79ce7e20f73d079c7)

---

## What it does

Takes three synthetic source representations of the same underlying financial events — **bank statement, invoice ledger, gateway settlement** — and runs them through a layered pipeline that ends in:

- A verified/conflict split with reason codes
- A value-weighted safety scorecard
- An append-only, hash-chained audit trail
- A structured review queue for unresolvable exceptions

**150 economic events × 3 sources = ~450 source records.** The problem requires 50+; we evaluate on a fixed 150-event frozen benchmark across four strict partitions (DEV, VALIDATION, TEST_ADVERSARIAL, FROZEN_UNSEEN).

---

## Architecture (Implemented)

```text
INGEST → DEDUP (Idempotency) → NORMALIZE
→ DETERMINISTIC MATCH (resolve cheap cases first)
→ BLOCK UNRESOLVED ONLY (naive pairs reduced 18x)
→ FUZZY EVIDENCE (RapidFuzz counterparty/reference)
→ SEMANTIC EVIDENCE (BGE-Small embeddings on desc)
→ PROBABILISTIC SCORER (Fellegi-Sunter, evidence families)
→ AMBIGUITY GATE (conf ≥ 0.60, gap < 0.10)
→ BATCHED LLM EVIDENCE (Qwen 3.6 27B bounded retries)
→ PROVISIONAL MATCH PROPOSAL
→ BOUNDED ALLOCATION (1:1 via SciPy)
→ INDEPENDENT FINANCIAL CONTROLS (CTRL-001…010)
→ FINAL DECISION: MATCH | REVIEW | NO_MATCH | PENDING
→ VALUE-WEIGHTED SCORECARD
```

AI proposes. Controls verify. Decision happens only after verification.

---

## Current Status: P1 & P2 COMPLETE

The backend matching pipeline (fuzzy + semantic + blocking + scoring) is strictly **frozen** and evaluated on a 150-event benchmark.

**Final Frozen Unseen Metrics (`FROZEN_UNSEEN`)**:
* **Safe automation rate**: 15.3%
* **False auto-match rate**: 0.0% (Perfect Safety)
* **Unsafe matches intercepted by Stage F controls**: 89
* **LLM Impact**: Validated to safely abstain (+0.0 delta) on highly corrupted data, adhering to all bounds with NO false matches.

### P2 Operator Features
Built transparently on top of the frozen pipeline:
* **Cryptographic Hash-Chained Audit Trail**: Tamper-evident ledger using SHA-256 for all decisions.
* **Stale Exception Tracking**: SLA enforcement prioritizing >24h unresolved reviews.
* **Conversational Q&A (Settlement Intelligence)**: LLM-powered context for finance operators to query why a decision was made.
* **Threshold Replay**: Simulate new confidence threshold rules safely in-memory without mutating the active ledger.

---

## Financial controls

| Control | Rule |
|---|---|
| CTRL-001 | No double allocation |
| CTRL-002 | Currency consistency |
| CTRL-003 | Settlement conservation |
| CTRL-004 | Gross/fee/tax/net consistency |
| CTRL-005 | No negative outstanding balance |
| CTRL-006 | Refund ≤ captured value |
| CTRL-007 | Lifecycle transition validity |
| CTRL-008 | Every source record has disposition |
| CTRL-009 | No duplicate event creates new allocation |
| CTRL-010 | Source semantics/Date Windows respected |

One failed control → `REVIEW`. Deterministic. No exceptions.

---

## Benchmark integrity

- `ground_truth_group_id` is **evaluator-only** — never enters `app/`
- `source_event_ids` are **opaque per-source UUIDs** — no lexical link between BANK/INVOICE/GATEWAY IDs for the same event
- Rarity statistics fitted on **DEV partition only** and frozen
- Evaluated completely blind on the FROZEN_UNSEEN partition.

---

## Quick start (Local Validation)

```bash
# 1. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest sentence-transformers

# 2. Run unit tests
PYTHONPATH=. pytest tests/ -v

# 3. Run the E2E non-LLM baseline
PYTHONPATH=. python scripts/run_e2e.py
```

---

## Hero metrics (Scorecard format)

1. **Safe automation rate** — MATCH / total decisions
2. **Value coverage %** — value verified / total value
3. **False auto-match rate** — wrong auto-matches / total auto-matches (Hard constraint: 0.0%)
4. **Review rate** — REVIEW / total decisions
5. **Adversarial holdout** — Final performance on unseen data
