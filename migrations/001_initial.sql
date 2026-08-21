-- ============================================================================
-- RazorLedger — Initial Schema Migration
-- Source of truth: 03-DESIGN.md A.1–A.9 + allocation_lines child table (fix #4)
-- Conventions:
--   • Money: BIGINT minor units + CHAR(3) currency. Never NUMERIC/FLOAT.
--   • PKs: UUID DEFAULT gen_random_uuid()
--   • Enums: TEXT + CHECK constraints (cheap to alter)
--   • Idempotency: UNIQUE(run_id, source, source_event_id) — run-scoped (fix #5)
-- ============================================================================

-- A.1 runs — one row per reconciliation run, the reproducibility anchor
CREATE TABLE runs (
    run_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_seed          TEXT NOT NULL,
    dataset_partition     TEXT NOT NULL CHECK (dataset_partition IN
                           ('DEV','VALIDATION','ADVERSARIAL_HOLDOUT','FROZEN_UNSEEN')),
    matcher_version       TEXT NOT NULL,
    embedding_model       TEXT NOT NULL,
    llm_model             TEXT NOT NULL,
    prompt_version        TEXT NOT NULL,
    code_commit           TEXT NOT NULL,
    run_cutoff_time       TIMESTAMPTZ NOT NULL,
    dataset_snapshot_hash TEXT NOT NULL,
    thresholds            JSONB NOT NULL,
    -- thresholds keys: auto_match_threshold, review_threshold,
    --                  minimum_confidence_gap, amount_tolerance,
    --                  date_tolerance, settlement_window_days
    status                TEXT NOT NULL DEFAULT 'RUNNING'
                           CHECK (status IN ('RUNNING','COMPLETE','FAILED')),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at          TIMESTAMPTZ
);

-- A.2 source_records — raw ingested rows, one per bank/invoice/gateway line
CREATE TABLE source_records (
    source_record_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id            UUID NOT NULL REFERENCES runs(run_id),
    source            TEXT NOT NULL CHECK (source IN ('BANK','INVOICE','GATEWAY')),
    source_event_id   TEXT NOT NULL,
    amount_minor_units BIGINT NOT NULL CHECK (amount_minor_units >= 0),
    currency          CHAR(3) NOT NULL,
    reference         TEXT,
    counterparty      TEXT,
    description       TEXT,
    transaction_date  DATE NOT NULL,
    lifecycle_state   TEXT NOT NULL CHECK (lifecycle_state IN
                       ('INITIATED','CAPTURED','PARTIALLY_SETTLED','SETTLED',
                        'REFUNDED','REVERSED','FAILED')),
    raw_payload       JSONB NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Fix #5: idempotency is run-scoped, not global.
    -- "Duplicate delivery within a run cannot create a second allocation."
    UNIQUE (run_id, source, source_event_id)
);
CREATE INDEX idx_source_records_run        ON source_records(run_id);
CREATE INDEX idx_source_records_blocking   ON source_records(run_id, amount_minor_units, transaction_date);
CREATE INDEX idx_source_records_ref        ON source_records(run_id, reference);

-- A.3 economic_events — the true reconciliation unit
CREATE TABLE economic_events (
    economic_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id            UUID NOT NULL REFERENCES runs(run_id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE economic_event_links (
    economic_event_id UUID NOT NULL REFERENCES economic_events(economic_event_id) ON DELETE CASCADE,
    source_record_id  UUID NOT NULL REFERENCES source_records(source_record_id),
    role              TEXT NOT NULL,  -- 'PRIMARY', 'SETTLEMENT_LEG', 'PARTIAL_PAYMENT'
    PRIMARY KEY (economic_event_id, source_record_id)
);

-- A.4 candidates — evidence computed for a proposed match, before decision
CREATE TABLE candidates (
    candidate_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                        UUID NOT NULL REFERENCES runs(run_id),
    source_record_id              UUID NOT NULL REFERENCES source_records(source_record_id),
    candidate_source_record_id    UUID NOT NULL REFERENCES source_records(source_record_id),

    -- Evidence features (fixed #3: evidence families, not raw field count)
    -- NUMERIC family
    amount_agreement              BOOLEAN,
    amount_difference_bin         TEXT,     -- 'EXACT','NEAR','CLOSE','FAR'
    -- TEMPORAL family
    date_delta_bin                TEXT,     -- 'SAME_DAY','NEAR','CLOSE','FAR'
    -- IDENTITY family
    reference_similarity_bin      TEXT,     -- 'EXACT','HIGH','MEDIUM','LOW'
    reference_similarity_score    REAL,
    counterparty_similarity_bin   TEXT,     -- 'HIGH','MEDIUM','LOW'
    counterparty_similarity_score REAL,
    -- SEMANTIC family
    description_similarity_bin    TEXT,     -- 'HIGH','MEDIUM','LOW'
    semantic_similarity_score     REAL,
    -- SOURCE family
    source_compatibility          BOOLEAN,
    evidence_rarity_score         REAL,

    -- Which families are satisfied (array of family names)
    -- Populated by evidence.py so the scorer can enforce the ≥2 family policy
    evidence_families_present     TEXT[],

    -- Probabilistic layer output
    probabilistic_confidence      REAL,
    confidence_gap_to_next        REAL,

    -- LLM evidence (only populated when LLM was invoked)
    llm_invoked                   BOOLEAN NOT NULL DEFAULT false,
    llm_supporting_evidence       JSONB,
    llm_contradicting_evidence    JSONB,
    llm_semantic_assessment       TEXT CHECK (
                                    llm_semantic_assessment IN ('supports','contradicts','neutral')
                                    OR llm_semantic_assessment IS NULL
                                  ),
    llm_stated_uncertainty        TEXT,

    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_candidates_run           ON candidates(run_id);
CREATE INDEX idx_candidates_source_record ON candidates(source_record_id);

-- A.5 decisions — FINAL post-control four-way outcome (fix #1: after controls, not before)
-- This table stores the outcome AFTER: allocation → controls → final decision.
-- Never write a MATCH here if controls have not yet passed.
CREATE TABLE decisions (
    decision_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id               UUID NOT NULL REFERENCES runs(run_id),
    source_record_id     UUID NOT NULL REFERENCES source_records(source_record_id),
    chosen_candidate_id  UUID REFERENCES candidates(candidate_id),
    action               TEXT NOT NULL CHECK (action IN ('MATCH','REVIEW','NO_MATCH','PENDING')),
    primary_reason       TEXT NOT NULL,
    -- e.g. CANDIDATE_MATCH, AMBIGUOUS_IDENTITY, NO_CANDIDATE, CONTROL_FAIL,
    --      INSUFFICIENT_EVIDENCE_FAMILIES, CONFIDENCE_GAP_INSUFFICIENT,
    --      BELOW_THRESHOLD, WITHIN_SETTLEMENT_WINDOW
    control_result       TEXT NOT NULL,
    -- e.g. 'PASS' or 'FAIL: CTRL-001' or 'FAIL: CTRL-003,CTRL-005'
    risk_exposure_score  REAL,           -- exposure × uncertainty × modifier heuristic
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_decisions_run_action ON decisions(run_id, action);

-- A.6 allocations — bounded 1:1 / 1:N / N:1 settlement allocation
-- Fix #4: source_record_ids UUID[] removed; individual lines in allocation_lines.
CREATE TABLE allocations (
    allocation_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id             UUID NOT NULL REFERENCES runs(run_id),
    allocation_type    TEXT NOT NULL CHECK (allocation_type IN ('ONE_TO_ONE','ONE_TO_N','N_TO_ONE')),
    economic_event_id  UUID NOT NULL REFERENCES economic_events(economic_event_id),
    -- Total of all allocation_lines must equal the sum below; verified by CTRL-003.
    total_amount_minor BIGINT NOT NULL,
    currency           CHAR(3) NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fix #4: explicit allocation lines so CTRL-005 and CTRL-003 can check per-record balances.
CREATE TABLE allocation_lines (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    allocation_id          UUID NOT NULL REFERENCES allocations(allocation_id) ON DELETE CASCADE,
    source_record_id       UUID NOT NULL REFERENCES source_records(source_record_id),
    allocated_amount_minor BIGINT NOT NULL CHECK (allocated_amount_minor > 0),
    currency               CHAR(3) NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_allocation_lines_alloc  ON allocation_lines(allocation_id);
CREATE INDEX idx_allocation_lines_record ON allocation_lines(source_record_id);

-- A.7 control_results — one row per invariant check, per invocation
CREATE TABLE control_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              UUID NOT NULL REFERENCES runs(run_id),
    control_id          TEXT NOT NULL CHECK (control_id IN (
                          'CTRL-001','CTRL-002','CTRL-003','CTRL-004','CTRL-005',
                          'CTRL-006','CTRL-007','CTRL-008','CTRL-009','CTRL-010'
                        )),
    status              TEXT NOT NULL CHECK (status IN ('PASS','FAIL')),
    message             TEXT,
    related_entity_ids  UUID[],
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_control_results_run ON control_results(run_id, control_id);

-- A.8 audit_log — append-only, optionally hash-chained
-- Application role must NOT have UPDATE/DELETE on this table.
CREATE TABLE audit_log (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id           UUID NOT NULL REFERENCES runs(run_id),
    entity_id        UUID NOT NULL,
    event_type       TEXT NOT NULL,
    old_state        TEXT,
    new_state        TEXT,
    primary_reason   TEXT,
    control_result   TEXT,
    action           TEXT,
    actor            TEXT NOT NULL,   -- 'SYSTEM' or 'HUMAN:<user_id>'
    matcher_version  TEXT,
    prompt_version   TEXT,
    previous_hash    TEXT,
    current_hash     TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_id);
CREATE INDEX idx_audit_log_run    ON audit_log(run_id);

-- A.9 review_queue — human-facing exception queue
CREATE TABLE review_queue (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                UUID NOT NULL REFERENCES runs(run_id),
    decision_id           UUID NOT NULL REFERENCES decisions(decision_id),
    status                TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','RESOLVED')),
    resolution_source     TEXT CHECK (
                            resolution_source IN ('HUMAN','SYSTEM')
                            OR resolution_source IS NULL
                          ),
    resolved_candidate_id UUID REFERENCES candidates(candidate_id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at           TIMESTAMPTZ
);
CREATE INDEX idx_review_queue_run_status ON review_queue(run_id, status);
