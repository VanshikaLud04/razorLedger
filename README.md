# RazorLedger — Verified Financial Reconciliation

> *"We didn't build a system that tries to reconcile everything. We built one that knows what it can safely reconcile."*

A multi-source financial reconciliation engine with deterministic financial controls, probabilistic evidence scoring, and an honest exception list.

---

## What it does

Takes three synthetic source representations of the same underlying financial events — **bank statement, invoice ledger, gateway settlement** — and runs them through a layered pipeline that ends in:

- A verified/conflict split with reason codes
- A value-weighted safety scorecard
- An append-only, hash-chained audit trail
- A structured review queue for unresolvable exceptions

**150 economic events × 3 sources = ~450 source records.** The problem requires 50+; we evaluate on a fixed 150-event frozen benchmark.

---

## Architecture (frozen — do not expand)

```
INGEST → DEDUP → NORMALIZE
→ DETERMINISTIC MATCH (resolve cheap cases first)
→ BLOCK UNRESOLVED ONLY
→ FUZZY EVIDENCE (RapidFuzz)
→ PROBABILISTIC SCORER (Fellegi-Sunter, evidence families)
→ (ambiguous only) LLM EVIDENCE (gemini-3.7-flash, thinking=low)
→ PROVISIONAL MATCH PROPOSAL
→ BOUNDED ALLOCATION (1:1 via SciPy / 1:N via bounded subset-sum DP)
→ INDEPENDENT FINANCIAL CONTROLS (CTRL-001…010)
→ FINAL DECISION: MATCH | REVIEW | NO_MATCH | PENDING
→ REASON-CODED, HASH-CHAINED AUDIT TRAIL
→ VALUE-WEIGHTED SCORECARD
```

AI proposes. Controls verify. Decision happens only after verification.

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
| CTRL-010 | Source semantics respected |

One failed control → `REVIEW`. Deterministic. No exceptions.

---

## Benchmark integrity

- `ground_truth_group_id` is **evaluator-only** — never enters `app/`
- `source_event_ids` are **opaque per-source UUIDs** — no lexical link between BANK/INVOICE/GATEWAY IDs for the same event
- Rarity statistics fitted on **DEV partition only** and frozen
- `test_matcher_cannot_import_truth_module()` enforces this at the AST level

---

## Quick start (local)

```bash
# 1. Start Postgres
docker compose up -d

# 2. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Copy and fill in env
cp .env.example .env
# Edit .env: add your GEMINI_API_KEY

# 4. Start the API
uvicorn app.main:app --reload

# 5. Run tests
pytest tests/ -v
```

---

## Configuration

All thresholds and model names live in `config/defaults.yaml`. Never hard-coded in business logic. Tune only on DEV/VALIDATION — never on holdout.

Key settings:
- `matching.auto_match_threshold`: minimum confidence to auto-match (default: 0.80)
- `llm.llm_max_evidence_delta`: LLM evidence cap (default: 0.05, tune on DEV)
- `dataset.records_per_partition`: 150 economic events

---

## Hero metrics (scorecard order)

1. **Safe automation rate** — true matches / total records
2. **Value coverage %** — value verified / total value
3. **False auto-match rate** — wrong auto-matches / total auto-matches
4. **Review burden %** — REVIEW decisions / total
5. **Adversarial holdout** (P1)

F1 is reported for internal analysis. It is not the pitch number.

---

## Milestone status

| Milestone | Status |
|---|---|
| P0: Trustworthy reconciliation engine | 🔨 In progress |
| P1: AI evidence layer (semantic + LLM) | ⏳ After P0 end-to-end run |
| P2: Presentation / polish | ⏳ After P1 |

**P0 is not the submission.** P1 adds the AI evidence layer that makes this an AI Finance Controller.

---

## What is NOT in this system

Per constitution: no N:N solver · no autonomous posting · no multi-agent · no forecasting · no tax matching · no fraud detection · no OCR · no RAG chatbot · no graph DB · no Kafka · no Redis · no pgvector · no fine-tuning · no RL.

One direction done rigorously beats four done shallowly.

---

## Sourcing note

All Razorpay-specific language refers only to public Razorpay product documentation. Nothing here claims to represent internal Razorpay architecture, policy, or roadmap.
