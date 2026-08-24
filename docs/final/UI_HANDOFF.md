# UI Designer Handoff Note

**Date**: 2026-08-24
**Status**: Backend FROZEN

## 1. Frozen Backend Architecture
The backend reconciliation engine has reached Absolute Freeze (Phase 7). The architecture leverages a bounded `OneToNAllocator` to solve structured N-way allocations and processes all candidates through strict constraints in the `FinancialControlEngine` (enforcing invariants like Conservation of Value). 

**CRITICAL:** Frontend work **must not** modify backend logic. Do not attempt to bypass controls, adjust thresholds, or restructure the core pipeline to support UI changes. The backend state is canonical and final.

## 2. Canonical Final Metrics
The exact numbers that should be reflected in the UI (or fetched from backend routes) are:
- **DEV Partition:** 343 / 450 (76.2% Safe Automation)
- **VALIDATION Partition:** 354 / 450 (78.6% Safe Automation)
- **TEST_ADVERSARIAL Partition:** 342 / 450 (76.0% Safe Automation)
- **FROZEN_UNSEEN Partition:** 358 / 450 (79.5% Safe Automation)
- **Overall Precision:** 100%
- **False Auto-Match Rate:** 0.0%

*Note: Any hardcoded claims of "~80-85%" or "80.2%" in the UI from earlier experimental phases are **stale** and should be removed or marked explicitly as superseded/historical.*

## 3. Data-Driven Fields
To prevent drift, the following fields in the UI should be built as dynamic, data-driven fields consuming JSON from the backend, rather than hardcoded HTML text:
- Dashboard Metrics (Safe Automation Rate, Review Queue count, False Auto-Match)
- Component allocations inside the "Allocation Visual" screen (Node amounts, entity counts, component structures)
- "Safe Match" and "Review" dispositions in the Review Queue.

## 4. Available Screens and Data Contracts
The UI currently supports the following structural views under `razorledger_ui_final2`:
- **Dashboard:** Consumes `PipelineResult` aggregates (`FINAL_SCORECARD.json`).
- **Allocation Visual / Command Center:** Displays 1:N and 1:1 components constructed by `OneToNAllocator`.
- **Review Queue / Forensic Review Workspace:** Displays `DecisionRecord` objects with explicit confidence scores, `primary_reason`, and `control_result` logs.

Please refer to `reports/final/FINAL_SCORECARD.json` for the exact final payload structure representing the global metrics.
