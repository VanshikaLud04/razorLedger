# Phase 6 Experiment Lineage

This document establishes the exact configuration and experiment lineage that led to the final frozen configuration (DEV matches = 343).

## The Discrepancy: 321 vs 343

During Phase 5, an initial experimental `OneToNAllocator` run produced **321 matches** on DEV. This allocator run, however, contained a safety gap: the 3-way Bank-Gateway-Invoice edges were being evaluated at a hardcoded `0.50` threshold rather than the canonical `0.80` required everywhere else in the system.

At the beginning of Phase 6, this rule was aggressively tightened: all edges in all components, regardless of cardinality, must strictly meet the `0.80` threshold. This enforcement corrected the baseline metric to **317 matches**.

Following this corrected baseline, a 5-step bounded optimization sequence was executed to safely maximize recall.

## Optimization Sequence

1.  **Baseline**: 317 DEV matches (strict 0.80 allocator).
2.  **Experiment 1 (Missing-Evidence Plumbing)**: Plumbed `description` to `semantic_similarity_bin` when semantic models are disabled.
    *   **Result**: 317 matches. Retained as a Correctness Fix.
3.  **Experiment 2 (Safe Punctuation Normalization)**: Stripped whitespace, hyphens, underscores, and periods inside `fuzzy.py`.
    *   **Result**: 322 matches. Retained.
4.  **Experiment 3 (Amount+Date Blocking)**: Added `Amount+Date` as a secondary blocking key. Critically removed an unsafe rule where amount+date bypassed the evidence scorer as a deterministic match.
    *   **Result**: 322 matches. Retained as a Crucial Safety Fix.
5.  **Experiment 4 (Prefix Normalization)**: Attempted to strip `INV-` and `TXN-` prefixes.
    *   **Result**: BLOCKED. No explicit repository evidence that these were formatting noise.
6.  **Experiment 5 (Bounded Allocator Decomposition)**: Upgraded `OneToNAllocator` to iteratively peel out and extract maximal disjoint valid subsets from rejected component hairballs.
    *   **Result**: 343 matches. Retained.

**Final DEV Result: 343 Matches (0 false auto-matches, 100% precision).**
