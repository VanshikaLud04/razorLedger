# Phase Index

## Phase 1 — Evaluation Infrastructure
**Goal**: Build rigorous evaluation infrastructure that prevents threshold gaming.
- **Files Created**: `evaluation/benchmark.py`, `evaluation/ablation.py`, `tests/test_benchmark_integrity.py`, `tests/test_ablation_equivalence.py`.
- **Files Modified**: `scripts/run_e2e.py`
- **Key Experiment**: Benchmark refactor preserving exactly 68 matches.
- **Key Finding**: Original numbers preserved exactly via `BenchmarkEvaluator`.
- **Final Decision**: Use `BenchmarkEvaluator` as sole source of truth.
- **Relevant Output**: `reports/baseline_scorecard.json`

## Phase 2 — Threshold Sweep
**Goal**: Find Pareto-optimal auto-match threshold.
- **Files Created**: `scripts/run_threshold_sweep.py`, `reports/threshold_sweep.csv`.
- **Key Experiment**: Swept threshold from 0.05 to 0.95.
- **Key Finding**: 0.80 maximizes automation (15.11%) with 0% false auto-match. Higher thresholds merely reduce coverage safely.
- **Final Decision**: Freeze threshold at 0.80.

## Phase 3 — Value Coverage / Review Burden Analysis
**Goal**: Analyze value-weighted automation vs record-weighted automation and identify burden groups.
- **Files Created**: `scripts/run_phase3.py`, `reports/value_coverage_analysis.json`, `reports/opportunity_ranked.csv`, `reports/value_coverage.png`, `reports/review_burden.png`.
- **Key Experiment**: Slice metrics by group size and review reason.
- **Key Finding**: Stage D adds value, Stage F blocks 100 unsafe provisions (CTRL-001). 205 records in REVIEW due to insufficient gap.
- **Final Decision**: Investigate root cause of blocked/rejected cases before modifying models.

## Phase 4 — Root Cause Validation
**Goal**: Validate if blocked/failed components are real dataset bugs or correct system behaviors.
- **Files Created**: `scripts/run_phase4.py`, `reports/blocking_failure_analysis.csv`, `reports/control_rejection_analysis.csv`.
- **Key Experiment**: Analyzed the 70 blocked records and 100 CTRL-001 failures against ground truth.
- **Key Finding**: 70 blocked cases lack deterministic references (correctly blocked). 100 CTRL-001 cases are valid 1:N/3-way allocations (Bank+Gateway+Invoice) failing sequential 1:1 tests.
- **Final Decision**: Create a 1:N Grouping Allocator to correctly assemble these components.

## Phase 5 — Safe Automation Recovery
**Goal**: Maximize safe automation while keeping false auto-match at 0%.
- **Files Created**: `scratch/experimental_allocator.py`, `scratch/test_experimental_allocator.py`, `scripts/run_phase5a.py`, `scripts/run_phase5b.py`, `scripts/run_phase5_research.py`.
- **Key Experiment**: Developed `OneToNAllocator` to capture 3-way matches atomically without bypassing `CTRL-001`. Experimented with Semantic/Reference weight tuning.
- **Key Finding**: Feature tuning did not safely resolve ambiguity. `OneToNAllocator` safely recovers ~71% automation across DEV/VALIDATION/ADVERSARIAL with 0% false matches.
- **Final Decision**: Validate allocator in Phase 6 and deploy if successful.
