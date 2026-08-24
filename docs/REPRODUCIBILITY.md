# Reproducibility Guide

This document outlines the steps to run RazorLedger's evaluation pipeline on the provided benchmarking partitions to reproduce the reported P1 findings.

## Prerequisites

- Python 3.11+
- Groq API Key (for LLM verification, optional for dry-runs)
- Set environment variables as defined in `.env.example`:
  ```bash
  GROQ_API_KEY="your-api-key"
  ```

## Setup Environment

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
pip install pytest sentence-transformers
```

## Running the Benchmark

You can execute the end-to-end reconciliation pipeline using the provided script. 

```bash
# Run baseline DEV evaluation
PYTHONPATH=. python scripts/run_e2e.py
```

The script will:
1. Initialize the `EconomicEventGenerator` with the `razorledger-dev-v1` seed.
2. Synthesize source records.
3. Pass records through the `ReconciliationPipeline` (including BGE embeddings and Financial Controls).
4. Output a scorecard and save a detailed JSON payload of the pipeline run.

To test across different partitions, modify `scripts/run_e2e.py` or use environment variables to switch between `DEV`, `VALIDATION`, `TEST_ADVERSARIAL`, and `FROZEN_UNSEEN`.

## Testing

Run the deterministic test suite:
```bash
PYTHONPATH=. pytest tests/ -v
```

This verifies that:
1. P1 architecture remains completely frozen and regression-free.
2. Edge cases around double-allocation and currency conflicts are handled correctly.
3. The cryptographic audit-chain generation is valid.
4. The simulation environment correctly isolates the primary production ledger.
