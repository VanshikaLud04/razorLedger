# RazorLedger Final Reproducibility Guide

**Date:** 2026-08-24
**Version:** 1.0.0 (Production Ready)

## Objective
This document outlines the exact steps required to reproduce the Final Freeze benchmark results for RazorLedger.

## Environment Setup
1. Clone the repository.
2. Ensure you have Python 3.13+ installed.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: The LLM integration is disabled by default in the final configuration, so valid Groq/Gemini API keys are not required to reproduce the final benchmark.)*

## Canonical Scripts
The repository contains only two canonical scripts for reproduction, located in `scripts/`:

1. **`run_final_benchmark.py`**: Runs the entire RazorLedger pipeline across all four data partitions (DEV, VALIDATION, TEST_ADVERSARIAL, FROZEN_UNSEEN) and compares the output against the original original deterministic baseline.
2. **`run_final_ablation.py`**: Runs a feature ablation (Stages A through F) on the DEV partition to demonstrate the incremental effect of fuzzy matching, semantic matching, rarity scoring, 1:N allocation, and financial verification.

## Execution

### 1. Run Final Benchmark
```bash
PYTHONPATH=. python scripts/run_final_benchmark.py
```
**Expected Output:**
Generates the following files in `reports/final/`:
- `FINAL_SCORECARD.csv`
- `FINAL_SCORECARD.json`
- `FINAL_CROSS_PARTITION.csv`
- `FINAL_DELTA_TABLE.csv`
- `FINAL_CONFIGURATION.json`

### 2. Run Final Ablation
```bash
PYTHONPATH=. python scripts/run_final_ablation.py
```
**Expected Output:**
Generates `FINAL_ABLATION.csv` in `reports/final/`.

### 3. Run Test Suite
```bash
PYTHONPATH=. pytest -v
```
**Expected Output:**
126 tests passed. No environment-only failures. No warnings.

## Configuration Details
The final outputs are strictly generated using `FINAL_CONFIGURATION.json`. No parameters (such as `auto_match_threshold=0.80`) should be modified. The pipeline is locked.
