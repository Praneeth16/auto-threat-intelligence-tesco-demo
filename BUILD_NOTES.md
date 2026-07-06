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

## Codex review (Stage 1)

Ran `/codex review` on the Stage 1 diff. Three findings, all fixed:
1. [P1] anchor normalization (fixed: floor to day).
2. [P2] overlap ground truth vs emitted feeds (fixed: derive from assignment).
3. [P2] invalid STIX identifiers (fixed: uuid5 + STIX timestamp format).
Regression tests added for all three (44 tests green).
