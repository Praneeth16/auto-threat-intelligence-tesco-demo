-- Lakebase (Postgres) operational-state schema for the Tesco SOC demo.
-- PLAN Section 6.1. Everything the UI touches on the hot path lives here.
-- Applied against the Lakebase database configured in workspace_config.
--
-- `findings` is populated by a Delta-to-Lakebase synced table (Stage 4 gold
-- output), so its rows are managed by the sync pipeline; the app reads it and
-- writes to the other tables. Idempotent: safe to re-apply.

-- ---------------------------------------------------------------------------
-- findings: synced from Delta gold_findings (read-hot for the Triage Board)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS findings (
    finding_id      TEXT PRIMARY KEY,
    domain          TEXT NOT NULL,
    risk_score      NUMERIC NOT NULL,
    components      JSONB,
    evidence        JSONB,
    intel_sources   TEXT[],
    first_seen      TIMESTAMPTZ,
    last_updated    TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'triaging', 'queued', 'auto_resolved',
                          'approved', 'rejected'))
);

-- ---------------------------------------------------------------------------
-- triage_queue: one row per finding the agent worked, awaiting human review
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS triage_queue (
    queue_id            BIGSERIAL PRIMARY KEY,
    finding_id          TEXT NOT NULL REFERENCES findings(finding_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    agent_run_id        TEXT,
    brief               TEXT,
    recommended_action  TEXT,
    action_tier         INT,
    agent_confidence    NUMERIC,
    judge_groundedness  NUMERIC,
    status              TEXT NOT NULL DEFAULT 'pending_review'
        CHECK (status IN ('pending_review', 'approved', 'rejected',
                          'auto_executed')),
    resolved_at         TIMESTAMPTZ,
    resolver_identity   TEXT
);
CREATE INDEX IF NOT EXISTS idx_triage_queue_status ON triage_queue(status);
CREATE INDEX IF NOT EXISTS idx_triage_queue_finding ON triage_queue(finding_id);

-- ---------------------------------------------------------------------------
-- decisions: the routing outcome for each finding (auto vs human queue)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decisions (
    decision_id          BIGSERIAL PRIMARY KEY,
    finding_id           TEXT NOT NULL,
    queue_id             BIGINT REFERENCES triage_queue(queue_id),
    route                TEXT NOT NULL
        CHECK (route IN ('auto_execute', 'human_queue')),
    action               TEXT,
    action_tier          INT,
    policy_version       INT,
    confidence_composite NUMERIC,
    executed             BOOLEAN NOT NULL DEFAULT false,
    reversible           BOOLEAN NOT NULL DEFAULT true,
    rollback_token       TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_decisions_finding ON decisions(finding_id);

-- ---------------------------------------------------------------------------
-- feedback_records: reason-coded verdicts from both lanes (human + auto audit)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback_records (
    feedback_id        BIGSERIAL PRIMARY KEY,
    decision_id        BIGINT REFERENCES decisions(decision_id),
    source             TEXT NOT NULL CHECK (source IN ('human', 'auto_audit')),
    verdict            TEXT NOT NULL CHECK (verdict IN ('agree', 'disagree')),
    -- Reason codes [exact] (PLAN 6.1).
    reason_code        TEXT CHECK (reason_code IN (
                           'wrong_classification', 'insufficient_evidence',
                           'wrong_action', 'policy_exception')),
    notes              TEXT,
    ground_truth_label TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- policy_store: versioned tier matrix the router reads
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policy_store (
    policy_id         BIGSERIAL PRIMARY KEY,
    version           INT NOT NULL,
    action            TEXT NOT NULL,
    tier              INT NOT NULL,
    auto_threshold    NUMERIC,
    requires_exact_ioc BOOLEAN NOT NULL DEFAULT false,
    notify            BOOLEAN NOT NULL DEFAULT false,
    reversible        BOOLEAN NOT NULL DEFAULT true,
    active            BOOLEAN NOT NULL DEFAULT true,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_policy_store_active ON policy_store(active, version);

-- allowlist: an allowlisted domain closes as benign citing its entry.
CREATE TABLE IF NOT EXISTS allowlist (
    domain      TEXT PRIMARY KEY,
    reason      TEXT,
    added_by    TEXT,
    decision_id BIGINT REFERENCES decisions(decision_id),
    version     INT,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- detections: proposed/approved/deployed Sigma rules with backtest metrics
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detections (
    detection_id     BIGSERIAL PRIMARY KEY,
    finding_id       TEXT,
    rule_yaml        TEXT,
    backtest_hits    INT,
    backtest_fp_rate NUMERIC,
    backtest_recall  NUMERIC,
    status           TEXT NOT NULL DEFAULT 'proposed'
        CHECK (status IN ('proposed', 'approved', 'deployed')),
    git_path         TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- replay_state: single-row control for the replay driver
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS replay_state (
    id             INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    sim_clock      TIMESTAMPTZ,
    speed          NUMERIC NOT NULL DEFAULT 1,
    running        BOOLEAN NOT NULL DEFAULT false,
    injected_paths TEXT[] NOT NULL DEFAULT '{}',
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO replay_state (id, sim_clock, speed, running)
VALUES (1, NULL, 1, false)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- case_memory: adjudicated cases the agent's search_case_memory tool reads.
-- Agent Bricks managed agent memory is the production store (PLAN 6.1); this
-- table is the GA-safe backing the read view exposes for the UI and the tool.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_memory (
    case_id           BIGSERIAL PRIMARY KEY,
    finding_signature TEXT NOT NULL,
    verdict           TEXT,
    reason_code       TEXT,
    brief_excerpt     TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_case_memory_signature ON case_memory(finding_signature);

-- Read view for the UI and the search_case_memory tool.
CREATE OR REPLACE VIEW case_memory_v AS
SELECT case_id, finding_signature, verdict, reason_code, brief_excerpt, created_at
FROM case_memory;
