# Manual configuration checklist (UI vs code)

Claude Code wrote all the code (datagen, pipelines, agent tools, router, judges,
FastAPI, React, Sigma, graph, SQL). These steps are Databricks configuration the
instructor performs (PLAN Section 15). Target workspace: `fe-vm-lakebase-praneeth`.

## One-time setup

1. **Catalog, schema, volume.** Created by `00_load_world`, or up front:
   `serverless_lakebase_praneeth_catalog.tesco_soc_demo` and the `soc_shared`
   volume. (Already created on the target workspace.)

2. **FMAPI endpoint.** Confirm a chat-capable pay-per-token endpoint exists and
   set its name in `SOC_LLM_ENDPOINT` (default `databricks-meta-llama-3-3-70b-instruct`,
   which returns chat content cleanly and accepts the enrichment params).

3. **Lakebase instance.** `tesco-soc-lakebase` (CU_1). Apply the schema and seed
   the policy store:
   ```bash
   PGHOST=<host> PGUSER=<you@databricks.com> SOC_LAKEBASE_INSTANCE=tesco-soc-lakebase \
     python -m app.db.apply_schema && python -m app.db.seed_policy_store
   ```

4. **Agent Bricks agents.** Register the triage and extraction agents from
   `agents/triage_agent/config.yaml` and `agents/extraction_agent/config.yaml`.
   Wire the MCP tools as Unity Catalog functions from `agents/tools/`.

5. **Genie space.** Create and curate the `soc_hunting` Genie space: table
   descriptions, synonyms, and three trusted questions (including the Act 3
   privileged-user question).

6. **AI Gateway.** Configure routes, budgets, and guardrails per
   `agents/gateway_config.py` (soc-enrichment and soc-agent routes).

7. **Lakebase synced tables.** Run `app/db/sync_config.py::create_findings_sync`
   after `gold_findings` exists, to sync gold to the Lakebase `findings` table.

8. **Detection Git folder + Job.** Point a Git folder at `detections/` and
   schedule a Job that runs the approved rules.

9. **Metrics dashboard.** Assemble the AI/BI dashboard or Unity Catalog Metrics
   for the Metrics Strip and screenshot it as a fallback.

10. **Deploy the App.** Build the frontend (`cd app/frontend && npm run build`),
    then `databricks apps deploy` per `app/app.yaml`. Attach the Lakebase and
    warehouse resources. Optionally configure Context-Based Ingress for external
    access. Set `SOC_REPLAY_JOB_ID` and `SOC_GENIE_SPACE_ID` env at deploy time.

## Deploy note (from prior AppKit experience)

If a Databricks App build container fails to fetch npm packages, the proxy
mirror may 404 tarballs the public registry serves. Generate `package-lock.json`
locally, then rewrite `resolved` hosts from the proxy to `registry.npmjs.org`
(same integrity hashes) so the container fetches from public npm. Do not add a
project `.npmrc` pinning the proxy.

## After first deploy

The App service principal rotates across redeploys. Re-read
`service_principal_client_id` from `databricks apps get` and re-grant UC SELECT,
warehouse CAN_USE, and the Lakebase role before expecting runtime data to work.

Record any version-specific deviation from documented behavior in `BUILD_NOTES.md`.
