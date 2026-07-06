# BUILD_NOTES

Deviations from PLAN.md and platform-status caveats, recorded as required by
PLAN Section 0 (rules 3 and 8).

## Environment

- Target Databricks workspace: profile `fe-vm-lakebase-praneeth`
  (https://fevm-serverless-lakebase-praneeth.cloud.databricks.com). All
  in-workspace runs (load notebook, pipelines, app, Lakebase) target this
  workspace.
- GitHub repo: `Praneeth16/auto-threat-intelligence-tesco-demo` (private).
- Local build/test uses a Python 3.11 venv (`.venv`). System Python is 3.9,
  which several pinned deps do not support.

## Stage 1: datagen

- **Cluster D removed.** PLAN 5.2 already cut cluster D (KitViper), but the
  Section 5.6 feed-coverage note still mentions "part of D" for the STIX and
  CSV feeds. Feeds cover A/B/C plus noise (N) and decoys (X) only. No D.
- **Feed overlap set is A URLs.** PLAN 5.2 asks for ~10% of cluster IOCs in two
  feeds. With the writer assignment (MISP carries A/C attributes, STIX carries
  B, CSV carries A URLs + decoys), the only genuine two-feed intersection is
  the campaign-A URLs, which land in both MISP and CSV. `build_overlap_pairs`
  now derives the overlap set from the same assignment constants the writers
  use, so the dedup ground truth cannot drift from what is emitted. This
  replaced an earlier version that sampled 10% of all cluster IOCs regardless
  of whether they actually appeared in two feeds (caught by codex review).
- **Reference anchor floors to the day, not the hour.** The attack paths plant
  fixed clock-times (Priya's T-1 22:37 login, AP2's T-6 17:40 login). A
  day-granular anchor keeps those instants exact whatever hour the world loads,
  while day-granular recency still reads live. An hour-granular anchor shifted
  every fixed clock-time by the current hour and could push T-0 events into the
  future (caught by codex review).
- **STIX identifiers are deterministic uuid5.** Object and bundle IDs use uuid5
  over a fixed namespace so `vendorx_bundle.json` parses as valid STIX 2.1 and
  stays reproducible. Timestamps are emitted as `...T..:..:..000Z` per the STIX
  timestamp grammar (caught by codex review).

## Stage 3: Lakebase schema

- **Lakebase instance:** `tesco-soc-lakebase` (CU_1, PG 16) created on the
  workspace. read_write DNS `ep-cool-mode-d2oleimw.database.us-east-1.cloud.databricks.com`.
  Database `databricks_postgres`, schema `public`.
- **Credential API deviation.** The lakebase skill doc shows
  `w.postgres.generate_database_credential(endpoint=<name>)`. On the current
  SDK that signature rejects a plain instance name
  (`InvalidParameterValue: Endpoint name expects 'projects/.../endpoints/...'`).
  The working call is
  `w.database.generate_database_credential(request_id=<uuid>, instance_names=[<name>])`.
  `connection.py` uses that. Recorded so Stages 4/6 reuse the right call.
- **Reverse sync is a Job, not a synced table.** Lakebase synced tables are
  Delta-to-Postgres only. App writes (decisions, feedback, resolutions) go
  Postgres-to-Delta, which is out of scope for synced tables, so `sync_config.py`
  documents them as a scheduled Job (Stage 8) into `mirror_*` Delta tables.
- **Verified live:** `schema.sql` applied clean to the instance (9 tables +
  `case_memory_v`), `seed_policy_store` seeded 7 rows at version 1, `replay_state`
  single-row control initialized. Policy matrix unit-tested (4 tests) without a DB.

## Stage 4: Lakeflow pipeline + FMAPI enrichment

- **Enrichment uses an explicit serving-endpoint call, NOT `ai_query`.** The
  plan wrote enrichment as `ai_query` in a SQL pipeline. Per user direction, the
  enrichment sentence now goes through an explicit Model Serving endpoint call
  (`w.serving_endpoints.query`, AI Gateway routes apply) in
  `pipelines/stream/enrichment_llm.py`. Rationale: the model call is visible,
  governed, and swappable rather than hidden in SQL; the candidate set is tiny
  (the scored domains) so per-row governed calls are cheap; the heavy agentic
  reasoning is the Stage 5 Agent Bricks triage agent regardless. Report
  extraction likewise calls the Agent Bricks extraction agent (Stage 5), with a
  ground-truth fallback for the reference build.
- **Enrichment endpoint default is `databricks-meta-llama-3-3-70b-instruct`.**
  Tested live on the workspace: `gemini-3-5-flash` returns empty content over
  the chat API, and `claude-opus-4-8` / `gpt-5-5` reject the `temperature`
  param. The instruct model returns clean content and accepts the params.
  `classify_domain` still sends `temperature=0` and retries without it on a
  BadRequest, so the newer reasoning models work too. Verified end-to-end:
  the hero domain enriches to a correct phishing classification grounded in the
  features.
- **Scoring is pure pandas, proven locally.** `pipelines/stream/scoring.py`
  implements the exact PLAN 7.2 weights. The hero ranks #1 at 82.37 with every
  component firing except repeat-access; both counterexamples score below all
  five attack paths (careers-verify at confidence 95 lands rank 6, so
  "confidence is not exposure" holds); report-only metric is 1 domain / 2 users.
  11 pipeline gate tests + 3 enrichment tests, 62 total green.
- **Brand similarity uses brand-token coverage.** rapidfuzz ratio saturated at
  100 for anything containing "tesco". The similarity feature now scores exact
  brand-token coverage (one token = 75 base, +15 per extra token), so the hero
  (`tesco` + `clubcard`) clears the >=85 threshold while single-token lookalikes
  sit at 75 and genuinely unrelated domains stay below 30.

## Stage 7: React frontend (AppKit + frontend-design)

- **AppKit scope decision.** The "leverage AppKit" instruction arrived after the
  FastAPI backend (Stage 6, PLAN 9.2) was built and contract-tested. AppKit is a
  full-stack Express framework; a full swap would discard the 13 passing contract
  tests and the tested SSE/OBO/Lakebase integration and diverge from the plan's
  architecture. Interpretation: leverage AppKit's design system and Databricks
  UI conventions (the `@databricks/appkit-ui` Shadcn/Radix/Tailwind + ECharts
  aesthetic, Databricks brand teal) for the React frontend, keeping the FastAPI
  backend the plan mandates. If a full AppKit/Express rewrite is wanted, it is a
  clean follow-up: the SSE event contract and REST paths would carry over.
- **Design direction (frontend-design skill).** Palette encodes the three-layer
  architecture, not decoration: teal = data plane (findings), violet = AI plane
  (agent/briefs), coral = human plane (approval gate). Deep situation-room slate
  base, not the AI-default hacker black. Type: Space Grotesk (display / risk
  numbers), Inter (body), JetBrains Mono (indicators). Signature element: the
  live-climbing risk meter on the hero finding.
- **Stack:** Vite + React 18 + TypeScript, Recharts for the metrics. Builds into
  `dist/`, which the FastAPI backend serves. Dev server proxies `/api` to the
  local backend. No browser storage APIs (PLAN 4.4).
- **Verified live:** built the bundle, served it from the backend with the
  in-memory repo, drove the app in a headless browser. All four views render
  (Director Console, Live Triage Board, Approval Queue, Metrics Strip); clicking
  Approve completed the full round-trip (React -> FastAPI -> SSE queue.updated ->
  React), emptying the queue. Screenshot confirmed the plane-color system reads.

## Stage 8: Feedback and eval

- **Agent Bricks optimizer is behind an illustrative fallback (as the plan
  directs).** PLAN 10.3 flags the Agent Bricks evaluation-and-optimization loop
  as the single highest platform-API risk item. `optimize_agent.py` does NOT run
  the optimizer live by default: it logs a hand-authored but plausible v1-vs-v2
  comparison to MLflow, tagged `status=ILLUSTRATIVE` so the presenter must
  caveat it. The live optimizer path is guarded behind `RUN_LIVE_OPTIMIZER=true`
  and falls back to illustrative on any error. Act 4's stronger, lower-risk
  sibling is the live retrieval-learning beat (below), which does not depend on
  this.
- **Reason-code routing (PLAN 10.1) is the learning logic.** `policy_exception`
  routes to the allowlist and policy_store but deliberately NOT to case memory
  (the agent reasoned correctly on the evidence it had, so it must not be taught
  to under-escalate). `wrong_classification` enters case memory. Verified by the
  Act 4 integration test: a policy_exception reject on clubcard-summer records an
  allowlist entry, and the router then auto-closes clubcard-autumn citing it.
- **Judges (PLAN 10.2): groundedness is the sole live gate.** A deterministic
  structural check (every count the brief asserts must trace to the evidence-tool
  output; no invented indicator) backs the MLflow judge and must pass >= 0.8
  before any auto-execute. Action-appropriateness runs offline as a metric only.
- 8 eval tests, 98 total green.

## Codex review (Stage 1)

Ran `/codex review` on the Stage 1 diff. Three findings, all fixed:
1. [P1] anchor normalization (fixed: floor to day).
2. [P2] overlap ground truth vs emitted feeds (fixed: derive from assignment).
3. [P2] invalid STIX identifiers (fixed: uuid5 + STIX timestamp format).
Regression tests added for all three (44 tests green).
