# FreshCart PhishOps: an agentic SOC on Databricks

A running, demo-able agentic security operations center built entirely from GA
Databricks primitives, driven from a React and FastAPI Databricks App. For a
security-engineering audience: the platform detects, agents investigate and
author, a human approves, and every decision becomes training data.

Working title on screen: **FreshCart PhishOps: 72 hours on the lakehouse.**

This is an architecture-and-demo, not a hands-on lab. The presenter drives a
live investigation from a UI while the room watches the platform detect, an
agent investigate, a human approve, and the system learn.

## What it is

Five layers, all inside one Unity Catalog governed workspace:

1. **Experience.** A Databricks App: React SPA served by a FastAPI backend, live
   over Server-Sent Events. Four views: Director Console, Live Triage Board,
   Approval Queue, Metrics Strip.
2. **Operational state.** Lakebase (serverless Postgres) holds everything the UI
   touches: triage queue, decisions, feedback, policy store, detections, replay
   state. Gold findings sync Delta-to-Lakebase for fast reads.
3. **Streaming intelligence.** A Lakeflow pipeline consumes replayed events,
   normalizes, enriches with a governed Foundation Model endpoint, scores, and
   writes gold findings. CTI reports are parsed and structured into silver.
4. **Agent plane.** An Agent Bricks triage agent investigates via MCP tools
   (Unity Catalog functions), writes a grounded brief, and recommends a tiered
   action. A Lakebase policy router enforces the tier-2 human gate.
5. **Feedback and evaluation.** MLflow 3 traces every agent run. Feedback becomes
   versioned eval datasets. A groundedness judge gates auto-execution. Rejections
   teach the system.

Two canonical diagrams live in `docs/`: the platform estate and the runtime flow.

## Requirements (for the Databricks admin)

Provision on the target workspace before the demo:

- Unity Catalog; serverless notebooks and serverless SQL.
- Foundation Model APIs (pay-per-token) enabled, with a chat-capable endpoint.
- Databricks Apps enabled.
- Lakebase (serverless Postgres) enabled.
- Agent Bricks enabled with FMAPI model access.
- Unity AI Gateway.
- MLflow 3.
- A Unity Catalog catalog and schema for the demo, plus a UC Volume.
- Git folder integration for detection export.
- Context-Based Ingress only if the audience opens the App externally.

No external dependencies: no VirusTotal, OTX, TAXII servers, or non-Databricks
model endpoints. All CTI feeds are static files the generator vendors. All model
calls go to FMAPI through AI Gateway.

## How to run

The build is validated on the `fe-vm-lakebase-praneeth` workspace with catalog
`serverless_lakebase_praneeth_catalog`, schema `tesco_soc_demo`, and Lakebase
instance `tesco-soc-lakebase`. All targets are configurable in
`pipelines/workspace_config.py` or via environment variables.

### 1. Local: generate and validate the world

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest datagen/tests            # ground-truth invariants
pytest                          # full suite (datagen, pipelines, agents, backend)
```

### 2. In-workspace: load the world

Sync this repo as a Databricks Git folder, then run the notebooks on serverless:

- `pipelines/00_load_world.py` (run once): datagen to UC Volume, tables, and CDF.
- `pipelines/99_validate.py`: the pre-demo hard-assert gate.

### 3. Lakebase schema

```bash
PGHOST=<instance-host> PGUSER=<you@databricks.com> \
  SOC_LAKEBASE_INSTANCE=tesco-soc-lakebase \
  python -m app.db.apply_schema
python -m app.db.seed_policy_store
```

### 4. Pipeline, agents, app

- Configure the continuous Lakeflow pipeline from `pipelines/stream/enrich_score.py`.
- Register the Agent Bricks triage and extraction agents from `agents/*/config.yaml`
  and wire the MCP tools (Unity Catalog functions in `agents/tools/`).
- Build the frontend and deploy the App:

```bash
cd app/frontend && npm install && npm run build
databricks apps deploy   # per app/app.yaml
```

See `docs/manual_setup.md` for the full instructor configuration checklist and
`RUNBOOK.md` for the demo-day script, timings, and fallbacks.

## Status honesty

Every platform feature used is GA as of the target date, except where noted.
Context-Based Ingress is public preview (optional). LTAP, Lakehouse//RT, managed
Omnigent, Genie App Builder, and Lakewatch appear only as forward-slide framing.
`BUILD_NOTES.md` records every deviation from the plan and every status caveat.

All indicators shown in the UI, briefs, reports, and this README are defanged.
