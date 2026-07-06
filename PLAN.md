# BUILD PLAN: Agentic Threat-Intel SOC Demo on Databricks

**Deliverable:** A running, demo-able agentic SOC on Databricks, driven from a React + FastAPI Databricks App, for a Tesco security-engineering audience (sits between software engineering and cybersecurity; deep threat-intel knowledge, new to Databricks).

**Format:** Architecture-and-demo, not a hands-on lab. The presenter drives a live investigation from a UI; the audience watches the platform detect, an agent investigate, a human approve, and the system learn.

**Working title (on-screen):** FreshCart PhishOps: 72 hours on the lakehouse.

**One-line thesis:** The platform detects, agents investigate and author, a human approves, and every decision becomes training data. An agentic SOC built entirely from GA Databricks primitives.

**Target platform version:** Databricks, July 2026 (post Data + AI Summit 2026). Uses FMAPI for enrichment and Agent Bricks for agents. Status of every platform feature used is tracked in Section 4.3; the presenter must be able to say truthfully which parts are GA and which are preview.

---

## 0. Reading order and non-negotiables (instructions to Claude Code)

Read this whole document before writing code. Build in the order in Section 1. Do not skip validation.

Hard rules, enforced everywhere:
1. **Ground-truth-first data.** The generator builds the attack storyline as explicit Python objects, renders data from them, then writes the ground truth as tables. Every detection, score, and agent decision in the demo must be rediscoverable from what the generator planted, and `datagen/tests` proves it. This is what makes a live demo safe.
2. **Determinism.** One seeded RNG (`seed=42`) for all data. Two generator runs produce identical output. The demo spine (the five attack paths) is fully scripted; only the filler pool is sampled, and it is pre-validated so every sampled event routes where expected.
3. **Status honesty.** Do not present a preview feature as GA. Where the build uses a preview/beta capability, isolate it behind a clearly named module and note it in `BUILD_NOTES.md` so the presenter knows to caveat it.
4. **No live weapon-of-demo risk.** Nothing generates attacker content live (no live LLM phishing generation, no attacker-vs-defender duel). The adversary is always replayed pre-generated data. Response actions are draft-plus-approval or reversible; tier-2 identity actions never auto-execute regardless of model confidence.
5. **Defang in display.** Every indicator shown in the UI, in any generated brief, in reports, in the README, or in slide-facing output is defanged (`[.]`). Plain form is allowed only inside data tables where matching is demonstrated. One `defang()` helper, used everywhere text is rendered.
6. **Voice.** All generated prose (agent briefs, report content, UI copy, markdown) follows the style guide in Section 14. No em dashes anywhere. No AI-patterned filler.
7. **Marked values.** Where a value is tagged **[exact]**, use it verbatim; the demo script and validation depend on it. Everything else is adjustable, but update the validation suite if you change it.
8. **Verify the API surface at build time.** This plan reflects the documented Databricks API as of July 2026. Before using `ai_query`, Agent Bricks agent registration, Lakebase synced tables, AI Gateway, MLflow 3 tracing, and Document Intelligence SQL functions, confirm the current signatures against official docs and adjust, recording deviations in `BUILD_NOTES.md`.

---

## 1. Build order

Build and validate in this sequence. Each stage must pass its checks before the next.

1. **`datagen/`** first. Pure Python + pandas, no Spark in core logic, locally testable. Produces the world, the filler pool, and all ground-truth tables. Gate: `pytest datagen/tests` green.
2. **Data load notebook** (`pipelines/00_load_world.py`). Thin wrapper that calls `datagen`, writes files to a UC Volume and tables to Unity Catalog, and syncs the read-hot tables to Lakebase. Gate: `pipelines/99_validate.py` green.
3. **Lakebase schema** (`app/db/`). Tables, sync config, seed policy store. Gate: schema applies clean, policy store seeded, synced tables readable.
4. **Lakeflow pipeline** (`pipelines/stream/`). Bronze to gold enrichment and scoring with FMAPI. Gate: replaying the AP1 event set produces the hero finding at the expected score.
5. **Agent plane** (`agents/`). Tools first (UC functions), then the triage agent, then the extraction agent, then the policy router, then gateway config. Gate: agent runs its full tool loop on the hero finding and writes a grounded brief; router sends the tier-2 action to the queue.
6. **FastAPI backend** (`app/backend/`). Endpoints, SSE, OBO auth, replay driver control. Gate: contract tests in Section 9.6 pass against a running Lakebase.
7. **React frontend** (`app/frontend/`). Four views. Gate: all four render against live SSE, director console controls the replay.
8. **Feedback and eval** (`agents/eval/`, `pipelines/eval/`). Reason codes, case memory, judges, the pre-baked v1-vs-v2 experiment. Gate: a rejection writes a feedback record and a case-memory entry; the v2 experiment renders.
9. **Detection export + graph** (`pipelines/detections/`, `pipelines/graph/`). Sigma to Git to Job; networkx clustering. Gate: rules validate through pySigma and a Job runs them; graph yields 3 labeled communities.
10. **Runbook + fallbacks** (`RUNBOOK.md`, director-console fallback buttons). Last.

---

## 2. Architecture

Five layers, all inside one Unity Catalog governed workspace.

### 2.1 Layer inventory

**Layer 1, Experience.** A Databricks App: React SPA served by a FastAPI backend, deployed serverless in the workspace (Databricks Apps, with horizontal autoscaling for a room of viewers). Live updates over Server-Sent Events. Four views: Director Console, Live Triage Board, Approval Queue, Metrics Strip. The app authenticates as its service principal for system actions but records approvals with on-behalf-of-user (OBO) identity so the audit trail names the human. If the audience opens the console on their own laptops, Context-Based Ingress (public preview) exposes the App under zero-trust policy.

**Layer 2, Operational state.** Lakebase (serverless Postgres) holds everything the UI touches on the hot path: `triage_queue`, `decisions`, `feedback_records`, `policy_store`, `detections`, `replay_state`. Gold findings sync Delta-to-Lakebase for millisecond reads; app writes sync back to Delta for analytics. Case memory uses Agent Bricks managed agent memory on Lakebase. Framing line for the room: this synced pattern is the shape LTAP formalizes (transactional and analytical workloads over one open-format copy, Lakebase for transactions, lakehouse for analytics).

**Layer 3, Streaming intelligence.** A continuous Lakeflow pipeline consumes replayed events from bronze Delta, normalizes, enriches with `ai_query` against FMAPI pay-per-token endpoints, scores, and writes gold findings. CTI reports land in a UC Volume, are parsed with Document Intelligence SQL functions (GA), and structured by an Agent Bricks Information Extraction agent into silver entities.

**Layer 4, Agent plane.** The triage agent is built on Agent Bricks. Its tools arrive over MCP: UC functions for telemetry and auth queries, a structured report-context lookup over the already-extracted `silver_report_entities`/`silver_report_summaries` tables (no separate vector index to provision, since Layer 3 has already turned the reports into queryable rows), and a Genie space for ad-hoc hunting. Databricks Sandbox gives it isolated execution for backtests. Every model call, from pipeline `ai_query` to agent turns, egresses through Unity AI Gateway (guardrails, budgets, usage, provider fallback). The tier-2 human gate is enforced primarily by the Lakebase policy router (GA-safe); managed Omnigent (beta) is shown on one forward slide as the out-of-prompt enforcement direction.

**Layer 5, Feedback and evaluation.** MLflow 3 traces every agent invocation. Feedback records sync Lakebase-to-Delta into versioned eval datasets. Judges gate groundedness before anything auto-executes. The nightly improvement job runs the Agent Bricks evaluation and optimization loop; v2 promotion is a traffic split on the serving endpoint (shadow, then promote). Lakehouse Monitoring watches decision tables for drift.

### 2.2 Two canonical diagrams to reproduce in `docs/`

Reproduce both as committed SVGs (or mermaid) so the repo carries the architecture:
- **Platform estate:** workspace container, App (React+FastAPI), Lakebase, Lakeflow+Delta, Agent Bricks, AI Gateway, MLflow 3, Git+Jobs, SOC team entering from outside. Color: coral human surface, teal data plane, purple AI plane.
- **Runtime flow:** Director Console → Lakeflow enrich+score (FMAPI) → Agent Bricks triage (fires on high-risk finding) → Policy router (tier × confidence, Lakebase) → auto-execute lane (audited, reversible) and approval queue (in-app, reason codes); verdicts loop back to MLflow evals, agent memory, policy store.

---

## 3. Repo structure [exact top level]

```
tesco-soc-demo/
├── README.md                       # what it is, requirements, how to run
├── BUILD_NOTES.md                  # every deviation from this plan, status caveats
├── RUNBOOK.md                      # demo-day script, timings, fallbacks
├── docs/
│   ├── architecture_estate.svg
│   └── architecture_runtime.svg
├── datagen/                        # the synthetic world (pure Python, locally testable)
│   ├── config.py                   # counts, names, seeds, campaign + filler specs
│   ├── entities.py                 # employees, groups, brand reference
│   ├── campaigns.py                # campaign infrastructure + IOC generation
│   ├── feeds.py                    # MISP JSON, STIX bundle, CSV feed writers
│   ├── reports.py                  # 13 unstructured reports + per-report ground truth
│   ├── telemetry.py                # dns/proxy/email/auth generators, planted paths
│   ├── filler.py                   # labeled filler-event pool (spine + noise)
│   ├── ground_truth.py             # consolidated ground-truth tables
│   └── tests/
│       └── test_invariants.py      # asserts every Section 5 payoff
├── pipelines/
│   ├── 00_load_world.py            # INSTRUCTOR run-once: datagen -> UC -> Lakebase sync
│   ├── 99_validate.py             # pre-demo gate
│   ├── classical/                  # deterministic CTI layer (open-source)
│   │   ├── ioc_regex.py            # iocextract pass over reports
│   │   ├── feed_parse.py           # STIX/MISP/CSV -> normalized silver_iocs
│   │   ├── typosquat.py            # tldextract + rapidfuzz brand-distance features
│   │   └── enrich_features.py      # registrar/ASN/passive-DNS-style feature build
│   ├── stream/
│   │   ├── replay_driver.py        # Job: writes spine + sampled filler to bronze
│   │   ├── enrich_score.py         # Lakeflow: classical features + ai_query, score, gold
│   │   ├── extract_reports.py      # regex + Doc Intelligence + Agent Bricks extraction
│   │   └── extraction_diff.py      # regex-vs-agent diff table (Act 1 beat)
│   ├── detections/
│   │   └── sigma_export.py         # findings -> Sigma yaml -> Git folder
│   ├── graph/
│   │   └── campaign_graph.py       # networkx clustering
│   └── eval/
│       ├── build_eval_dataset.py   # feedback -> versioned MLflow eval set
│       └── optimize_agent.py       # Agent Bricks optimize; produces v1-vs-v2 run
├── agents/
│   ├── tools/                      # UC function source for MCP tools
│   │   ├── query_telemetry.py
│   │   ├── check_auth_anomalies.py
│   │   ├── get_user_context.py
│   │   ├── get_campaign_cluster.py
│   │   ├── lookup_policy.py
│   │   ├── search_case_memory.py
│   │   └── get_report_context.py
│   ├── triage_agent/               # Agent Bricks config + prompt + registration
│   ├── extraction_agent/           # Information Extraction agent config
│   ├── router/
│   │   └── policy_router.py        # tier x confidence routing over policy_store
│   └── eval/
│       ├── judges.py               # groundedness + action-appropriateness judges
│       └── reason_codes.py         # feedback taxonomy + routing of feedback
├── app/
│   ├── db/                         # Lakebase schema + migrations + seed
│   │   ├── schema.sql
│   │   ├── sync_config.py          # Delta<->Lakebase synced tables
│   │   └── seed_policy_store.py
│   ├── backend/                    # FastAPI
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── sse.py
│   │   ├── auth.py                 # OBO identity capture
│   │   └── replay_control.py
│   ├── frontend/                   # React (Vite)
│   │   ├── src/views/              # DirectorConsole, TriageBoard, ApprovalQueue, Metrics
│   │   ├── src/components/
│   │   └── src/sse.ts
│   ├── app.yaml                    # Databricks App config
│   └── tests/
│       └── test_contract.py        # backend contract tests
└── requirements.txt
```

---

## 4. Environment and platform requirements

### 4.1 Workspace requirements (state in README for the Tesco admin)
Unity Catalog; serverless notebooks and serverless SQL; Foundation Model APIs (pay-per-token) enabled; Databricks Apps enabled; Lakebase enabled; Agent Bricks enabled with FMAPI model access; Unity AI Gateway; MLflow 3; a UC catalog and schema for the demo; Git folder integration for detection export. Context-Based Ingress only if the audience opens the App externally. (Vector Search is not required: report retrieval uses the already-extracted structured tables, Section 8.3.)

### 4.2 No external dependencies
No VirusTotal, OTX, TAXII servers, or non-Databricks model endpoints. Only network egress is PyPI/npm at build time. All CTI feeds are static files vendored by the generator. All model calls go to FMAPI through AI Gateway.

### 4.3 Feature status table (drives Section 14 caveats and the forward slide)

| Capability | Used for | Status (Jul 2026) | Demo treatment |
|---|---|---|---|
| FMAPI pay-per-token | all enrichment `ai_query` | GA | Live |
| Agent Bricks (agents, memory via Lakebase, Sandbox) | triage + extraction agents, case memory | GA (expanded) | Live |
| Document Intelligence SQL functions | report parsing | GA | Live |
| Unity AI Gateway | model routing, guardrails, budgets, fallback | GA | Live |
| Lakebase (Postgres, synced tables) | operational state | GA | Live |
| Lakeflow | streaming enrichment | GA | Live |
| Databricks Apps (autoscaling) | the SOC console | GA | Live |
| MLflow 3 (tracing, evals, judges) | agent observability + eval | GA | Live |
| AI/BI dashboards, Unity Catalog Metrics | metrics strip source | GA / recent | Live |
| Context-Based Ingress | expose App externally | Public Preview | Optional, caveat |
| LTAP | the synced-tables framing | New/architectural | Slide framing only |
| Lakehouse//RT | ultra-fast reads | Private Preview | Mention only |
| Managed Omnigent | out-of-prompt human-gate enforcement | Beta | One forward slide |
| Genie App Builder, Genie ZeroOps | "what's next" | Beta | Mention only |
| Lakewatch | agentic SIEM | Private Preview | One closing mention, deprioritized |

### 4.4 Packages
Python (pin at build time): `pandas`, `faker`, `pyyaml`, `tldextract`, `rapidfuzz`, `iocextract`, `stix2`, `pymisp`, `networkx`, `pysigma`, `pysigma-backend-splunk`, `databricks-sdk`, `mlflow>=3`, `fastapi`, `uvicorn`, `sse-starlette`, `psycopg[binary]` (or the Lakebase-recommended driver), `pydantic`. Node/React: Vite, React 18, a lightweight chart lib for the metrics strip, an SSE client. No browser storage APIs.

### 4.5 Data scale
Deliberately small so every cell and endpoint is sub-second. Largest telemetry table 60k rows. Scale is a talking point, not a requirement.

---

## 5. Synthetic data specification

The heart of the build. Ground truth first, every element earns a payoff, one hero finding threads the whole demo.

### 5.1 Design principles
1. **Ground truth first**, as in Section 0.
2. **Every planted element has a payoff** (mapping in 5.9). If it has no payoff, cut it.
3. **Signal, decoys, dead noise.** Real feeds are mostly noise. Of 455 structured IOCs, 200 never appear internally (dead noise), 30 are high-similarity but benign decoys (false-positive discussion), and only the planted paths produce true findings.
4. **One hero finding** (AP1) threads every act; its name is said out loud in each act, and the final grounded brief about it is the emotional payoff.
5. **Time is relative and feels live.** All timestamps are offsets from `REFERENCE_TS = date_trunc('hour', now())` computed when the world loads. `T-2` means 2 days before reference. Offsets are deterministic; only the anchor moves. Recency reads "first seen 3 days ago" on demo day.

Safety and realism:
- Employee email domain **[exact]**: `@tesco-demo.example`. Never `@tesco.com` for synthetic people.
- Attacker domains are plausible strings (needed for the similarity demo) but defanged in all display/brief/report/README/slide output. Plain form only inside data tables.
- Protected-brand reference (the legitimate premise) **[exact]**: `tesco.com`, `tescobank.com`, `tescoplc.com`, `tescomobile.com`, `tesco.ie`, plus tokens `clubcard`, `tesco`.

### 5.2 Campaign universe

Three clusters plus noise and decoys. Each cluster has a distinct shared-infrastructure fingerprint so the graph cleanly separates them. (A fourth cluster was considered purely to make the graph reveal say "4" instead of "3" campaigns; cut, since the extra campaign's infrastructure, kit fingerprint, and dedicated reports cost real build effort for a one-digit difference in a 30-second reveal. Three campaigns collapsing out of hundreds of indicators is the same story.)

| ID | Campaign name | Theme | IOC count | Hosting IPs | ASN label | Registrar | Registrant email | Kit fingerprint |
|----|---------------|-------|-----------|-------------|-----------|-----------|------------------|-----------------|
| A | **FreshCart PhishOps** [exact] | Clubcard/rewards credential phishing | 120 (45 domains, 30 URLs, 25 IPs, 12 sender emails, 8 hashes) | 185.163.44.10-15 | AS208877 "BulletHost-Demo" | NameDodger LLC | hostmaster@freshcart-ops.example | `/wp-login-secure/` + `fc-kit-v3` |
| B | **SupplierPay** | Supplier/invoice BEC vs finance | 60 | 45.148.121.20-23 | AS49392 "FastFlux-Demo" | QuickReg Ltd | billing-admin@supplierpay.example | `/portal/login` + `sp-kit-1` |
| C | **CareerLure** | Fake recruitment vs jobseekers | 45 | 103.152.78.5-7 | AS135377 "CloudCheap-Demo" | DomainsRUs | hr-verify@careerlure.example | `/apply/verify` + `cl-kit-2` |
| N | (noise) | Unrelated C2/ransomware/scanner | 200 | random | random | random | random | none |
| X | (decoys) | Benign lookalikes | 30 domains | shared consumer hosting | AS16509-style | mixed | none | none |

Total structured IOCs: **455** [exact].

**Feed overlap:** ~10% of cluster IOCs appear in two feeds with slightly different confidence (forces the dedup step).

**Named domains that must exist [exact]:**
- A: `tesco-clubcard-support.com` (the hero), `tesco-rewards-login.com`, `tescobank-secure-auth.com`
- B: `tesco-supplier-billing.com`
- C: `tesco-careers-verify.com`
- X decoy: `tesco-fans-forum.com` (similarity ~78, confidence 20, tag `unverified`, 3 benign visits)
- Report-only (in NO structured feed): `tesco-parcel-tracking.net`
- **Vendor false-positive [exact, new]:** `clubcard-summer-deals.com`, registered by Tesco's own marketing agency, looks phishy by every automated signal (high brand similarity, recently registered, consumer hosting), but is legitimate. Powers the policy-exception learning beat (Act 4). Plus a sibling `clubcard-autumn-deals.com` used to demonstrate auto-close from case memory after the exception is recorded.

Generate remaining lookalikes programmatically (token pools + connectors + TLDs + a few homoglyph/typo variants at varying edit distances) so the similarity threshold has texture.

### 5.3 People

`ref_employees`: **200 rows**. Columns: `employee_id`, `full_name`, `email`, `department`, `job_title`, `ad_groups` (array), `is_privileged` (12 true; members of `Cloud-Admins`, `Domain-Admins`, or `Payments-Ops`), `is_vip` (5 true), `office_location` (Welwyn Garden City, London, Dundee, Bengaluru), `usual_country` (GB or IN by location).

Named characters **[exact]** (Faker fills the rest):
- **Priya Nair**, Senior Cloud Platform Engineer, Cloud Platform, `Cloud-Admins`, Bengaluru, `is_privileged=true`. The privileged victim in AP1.
- **Mark Whitfield**, Accounts Payable Analyst, Finance, `AP-Team` (deliberately NOT privileged, so AP1 stays the only privileged-user finding in the top 5), Welwyn Garden City. Victim in AP2.
- **Sophie Clarke**, Customer Care Advisor, Customer Care, Dundee. The repeat visitor in AP5.

### 5.4 The five planted attack paths

All offsets from `REFERENCE_TS`. All recorded verbatim in `gt_attack_paths`.

**AP1, the hero.** FreshCart credential harvest via `tesco-clubcard-support[.]com`.
- Feed: RetailISAC-Demo, confidence 90, first_seen T-6, tags `phishing, credential-harvesting`, MITRE `T1566.002`.
- T-2 09:14: email wave, sender `rewards@tesco-clubcard-support.com`, subject **[exact]** "Action needed: your Clubcard points expire in 48 hours", to 60 employees.
- **17 distinct employees** [exact] click T-2 09:20 to T-1 18:00 (email + matching proxy GET to `/wp-login-secure/index.php` + DNS).
- **3 of the 17** [exact] (Priya Nair + 2 Faker employees) submit credentials: proxy POST, ~200-400 bytes up.
- Auth: each of the 3 shows **5-8 failed logins 20-45 minutes after their click** [exact], then a lockout. Priya additionally has a **successful** login at T-1 22:37 from `country=RO`, ASN "GreyStack-Demo", device `unknown`.
- Expected: **rank #1** in gold findings, all scoring components firing except repeat-access.

**AP2, BEC.** `tesco-supplier-billing[.]com`, victim Mark Whitfield.
- Feed: VendorX ThreatFeed (STIX), confidence 75, first_seen T-9.
- T-6 11:02 email "Updated bank details for PO 4471182"; Mark clicks T-6 11:09; proxy POST to `/portal/login`; successful anomalous login T-6 17:40 `country=RO`.
- Expected: rank #2. Teaches identity-context + geo-anomaly.

**AP3, the feed gap.** `tesco-parcel-tracking[.]net`.
- In **only** report R14, never any structured feed **[exact]**.
- Internal DNS: 2 employees at T-4.
- Expected: after extraction merges it into silver, it surfaces as a finding whose only source is `report_ai_extraction`. The "AI found what the feeds missed" moment. Pipeline computes the metric: report-only findings = 1 domain, 2 users.

**AP4, the fresh one.** `tescobank-secure-auth[.]com`.
- Feed first_seen **T-1 06:00**; DNS T-1 14:00 (3 users), T-0 08:00 (1 user). No credential entry, no auth anomalies.
- Expected: high recency pushes it to rank #3 despite modest exposure.

**AP5, the bookmark.** `tesco-rewards-login[.]com`.
- Sophie Clarke visits **9 times across T-3..T-1** [exact]. No failed logins.
- Expected: repeat-access flag fires; rank #4 or #5.

**Teaching counterexamples (must exist, not attack paths):**
- `tesco-careers-verify[.]com`: confidence 95 (highest) but exactly **1** internal DNS hit from guest-wifi. Scores below all APs. Confidence is not exposure.
- `tesco-fans-forum[.]com`: similarity ~78, 3 benign visits, confidence 20. Mid-table. Similarity is not verdict.
- 200 noise IOCs: zero internal hits. Most intel is about things that never touched you.

### 5.5 The filler pool (new, powers "keep generating")

`filler.py` produces **~120 template events** (down from an earlier ~300-500 plan; enough to make the stream feel alive and give the auto-lane real throughput, without the extra generation and validation cost of a much larger pool that adds no new narrative). Categories and expected routing:

| Category | Count | Ground-truth label | Expected route |
|---|---|---|---|
| Commodity phish, exact known-bad IOC match | ~50 | true_positive_low | tier-0 auto (watchlist/close), no agent |
| Scanner / recon noise | ~35 | benign_noise | pre-filter close, no agent |
| Known false positives (duplicate of prior benign) | ~20 | benign_dup | pre-filter close (dedup) |
| Ambiguous lookalike, low corroboration | ~15 | needs_review | agent triages, usually queue |

Deliberately cut: a generic "vendor-adjacent lookalike" filler category. It would produce random policy-exception events during Act 2 replay, which risks the audience seeing a policy-exception resolution before Act 4's scripted reveal and diluting it. The clubcard-summer/autumn pair (Section 5.2) is director-injected, not sampled, and is now the only source of that beat.

At demo time, clicking Run samples from the pool, rewrites timestamps to now, and streams events in. The five attack paths are injected by director-console buttons, not sampled, so the storyline is exact. `datagen/tests` asserts every pool item's label matches where the router would send it.

### 5.6 Files written by the load notebook

**Raw files in Volume** `/Volumes/{catalog}/soc_shared/raw/`:
- `feeds/misp/retailisac_demo_event_{1..3}.json` (loadable by `pymisp.MISPEvent`), ~200 attributes covering A, C, part of N.
- `feeds/stix/vendorx_bundle.json` (valid STIX 2.1, single-comparison patterns), ~180 indicators covering B, D, part of N.
- `feeds/csv/openphish_style.csv` (`url,discovered_ts,confidence`), ~150 rows, A/D URLs + decoys.
- `reports/` (13 report files per the sparse IDs in Section 5.7, `.md`/`.txt`/`.html`) and matching `reports/ground_truth/R##.json`.
- `reference/brand_assets.csv`, `reference/benign_top_domains.csv` (~1,000 popular domains for benign traffic vocabulary).

**Bronze telemetry tables** (Delta; ingestion plumbing out of scope, point to Lakeflow Connect on the roadmap):

| Table | Rows | Columns |
|---|---|---|
| `bronze_dns_logs` | 60,000 | `ts, employee_id, src_ip, query_domain, query_type, response_ip, source_tag` (corp/vpn/guest-wifi) |
| `bronze_proxy_logs` | 25,000 | `ts, employee_id, src_ip, method, url, domain, status, bytes_out, bytes_in, user_agent, category` |
| `bronze_email_events` | 6,000 | `ts, employee_id, msg_id, sender, subject, url_clicked, action` (delivered/clicked/reported) |
| `bronze_auth_logs` | 9,000 | `ts, employee_id, app, result` (success/failure/lockout)`, country, asn_label, device` |

Benign background: departmental browsing from `benign_top_domains`, office-hours weighting per local timezone, weekend dips, a base rate of scattered auth failures so AP bursts stand out statistically.

**Reference tables:** `ref_employees`, `ref_brand_assets`, `ref_ioc_enrichment` (`indicator_value, hosting_ip, asn_label, registrar, registrant_email, kit_id`; populated for A-D, null for N/X; consumed by the graph).

**Ground-truth tables:** `gt_campaigns`, `gt_attack_paths` (expected evidence counts per AP), `gt_expected_findings` (expected top-5 domains in rank order with tolerance), `gt_report_entities`, `gt_filler_labels` (Section 5.5).

**Reference outputs for the pipeline to target:** `silver_iocs_ref`, `silver_report_entities_ref`, `gold_findings_ref`. Produced by calling the same transform functions the pipeline uses, so reference and live outputs cannot drift.

### 5.7 The 13 unstructured reports
Vary format and voice; extraction robustness is the point. Down from an earlier 20-report plan: cutting KitViper's dedicated reports (gone with cluster D) and trimming the noise set from five reports to two removes real authoring effort (each report needs to read as competent vendor/analyst prose, not mad-libs) without losing any payoff-mapped element. IDs are sparse rather than sequential (gaps where cut reports used to sit) so that R14 and R15, referenced by exact ID elsewhere in this plan and in the runbook, keep the same identity.
- **R01-R05, FreshCart** (5 reports): vendor blog, ISAC advisory, DFIR writeup, social thread, takedown email. R02/R04 fully defanged with `hxxps`/`[.]`. Include alias "TA-FreshCart", `fc-kit-v3`, MITRE `T1566.002`/`T1539`, hero domain in at least 3.
- **R06-R07, SupplierPay** (2 reports, down from 3): invoice-fraud advisory, bank alert.
- **R09-R10, CareerLure** (2 reports): consumer-protection blog, HR ISAC note. Low enterprise relevance, feeds the counterexample.
- **R14, feed-gap [exact, ID fixed]:** regional CERT advisory, contains `tesco-parcel-tracking[.]net` + one IP `194.5.249.211` [exact] in no feed, 600-800 words, defanged.
- **R15, exclusive-but-quiet [exact, ID fixed]:** one sender + one URL in no feed and no telemetry; extraction still enriches the watch list.
- **R19-R20, unrelated noise** (2 reports, down from 5): extraction must not hallucinate brand relevance; `targeted_brands` empty or unrelated.

Each report 300-900 words, realistic prose not mad-libs. Every planted entity goes into its `ground_truth/R##.json` (`actors, iocs[{value,type}], ttps, targeted_brands, kit_ids, recommended_detections_present`).

### 5.8 Extraction schema (shared by extraction agent and eval)
JSON fields: `actors[]`, `iocs[{value,type}]`, `ttps[]` (MITRE IDs), `targeted_brands[]`, `phishing_kits[]`, `confidence` (low/medium/high), `summary` (string), `recommended_detections[]`.

### 5.9 Payoff map (build check)

| Planted element | Pays off in |
|---|---|
| Feed overlap duplicates | pipeline dedup step (classical feed_parse) |
| STIX/MISP/CSV feeds | classical ingestion the room recognizes |
| Defanged + prose-described IOCs in reports | regex-vs-agent extraction diff (Act 1) |
| Registrar/ASN/hosting in ref_ioc_enrichment | classical enrichment features feeding the score |
| Homoglyph/edit-distance variety | typosquat distance feature, threshold discussion |
| Hero similarity >= 85 | validation assert, Act 1 |
| R19-R20 irrelevance | extraction schema discipline |
| R14 feed-gap domain | extraction anti-join reveal + report-only finding (Acts 1-2) |
| AP1 click-to-failed-login timing | temporal correlation, agent evidence |
| Priya's privileged group | business-context routing to tier-2 (Act 3) |
| AP2 geo anomaly | auth anomaly, agent evidence |
| AP4 freshness | recency component |
| AP5 nine visits | repeat-access flag |
| CareerLure high-confidence/low-exposure | scoring + agent reasoning discussion |
| Decoy fans-forum | false-positive discussion |
| clubcard-summer/autumn family | policy-exception + auto-close-from-memory (Act 4) |
| Filler pool labels | pre-filter and auto-lane demonstration |
| Cluster fingerprints (hosting, kit id) | graph clustering (Act 4) |
| gt_expected_findings order | validation rank assertions |

---

## 6. Layer 2: Lakebase operational state

### 6.1 Tables (`app/db/schema.sql`)

- `findings` (synced from Delta gold): `finding_id (pk), domain, risk_score, components jsonb, evidence jsonb, intel_sources text[], first_seen, last_updated, status` (new/triaging/queued/auto_resolved/approved/rejected).
- `triage_queue`: `queue_id (pk), finding_id (fk), created_at, agent_run_id, brief text, recommended_action text, action_tier int, agent_confidence numeric, judge_groundedness numeric, status` (pending_review/approved/rejected/auto_executed), `resolved_at, resolver_identity`.
- `decisions`: `decision_id (pk), finding_id, queue_id, route` (auto_execute/human_queue)`, action text, action_tier int, policy_version int, confidence_composite numeric, executed bool, reversible bool, rollback_token text, created_at`.
- `feedback_records`: `feedback_id (pk), decision_id, source` (human/auto_audit)`, verdict` (agree/disagree)`, reason_code text, notes text, ground_truth_label text, created_at`. Reason codes **[exact]**: `wrong_classification`, `insufficient_evidence`, `wrong_action`, `policy_exception`.
- `policy_store`: `policy_id (pk), version int, action text, tier int, auto_threshold numeric, requires_exact_ioc bool, notify bool, reversible bool, active bool, updated_at`. Plus `allowlist(domain pk, reason text, added_by text, decision_id, version int, added_at)`.
- `detections`: `detection_id (pk), finding_id, rule_yaml text, backtest_hits int, backtest_fp_rate numeric, backtest_recall numeric, status` (proposed/approved/deployed)`, git_path text, created_at`.
- `replay_state`: single-row control: `sim_clock timestamptz, speed numeric, running bool, injected_paths text[], updated_at`.
- Case memory: use Agent Bricks managed agent memory on Lakebase; expose a read view `case_memory_v` for the UI and the `search_case_memory` tool (`case_id, finding_signature, verdict, reason_code, brief_excerpt, created_at`).

### 6.2 Sync (`app/db/sync_config.py`)
Delta gold `gold_findings` syncs to Lakebase `findings` (continuous or short-interval). App writes (`decisions`, `feedback_records`, `triage_queue` resolutions) sync back to Delta mirror tables for MLflow eval and Lakehouse Monitoring. Document the direction and cadence.

### 6.3 Seed (`app/db/seed_policy_store.py`)
Seed policy_store version 1 with the tier matrix in Section 8.4 and an empty allowlist. Idempotent.

---

## 7. Layer 3: Lakeflow streaming + FMAPI enrichment

### 7.1 Replay driver (`pipelines/stream/replay_driver.py`)
A Job (triggered by FastAPI) that reads spine events (the five attack paths) and sampled filler, rewrites timestamps relative to `replay_state.sim_clock`, and appends to bronze Delta at the configured speed (72 simulated hours in ~6 wall minutes). Supports: start(scenario, speed), inject(path_id), pause, seek(to_ts). Writes progress to `replay_state`. Every write is a discrete micro-batch so the stream visibly advances.

### 7.2 Enrichment and scoring (`pipelines/stream/enrich_score.py`)
Continuous Lakeflow pipeline: bronze -> normalize to a common event shape -> join `silver_iocs` (exact + fuzzy against brand assets via a `rapidfuzz` UDF) -> attach classical enrichment features (Section 7.4) -> enrich suspicious domains with `ai_query` on an FMAPI endpoint (through AI Gateway) for a short structured classification that reasons over those features -> compute the risk score -> write `gold_findings`. The `ai_query` endpoint name is config (`llm_endpoint`, default a chat-capable FMAPI model, e.g. `databricks-claude-sonnet-4-5`); a config cell lists available endpoints and picks a fallback if the default is absent.

The division of labor is deliberate and stated on stage: the classical layer (feed parsing, IOC regex, typosquat distance, registrar/ASN features) builds the structured features and the transparent score; the AI layer reasons over those features plus the unstructured reports. Feature engineering is classical; synthesis and explanation are AI.

Risk score **[exact starting weights]**:
```
risk_score =
    25 * (max_source_confidence / 100)
  + 20 * least(distinct_users_hit / 10.0, 1.0)
  + 15 * exp(-days_since_first_seen / 7.0)
  + 15 * (brand_similarity_score / 100)
  + 10 * credential_entry_flag          -- any POST to a kit path
  + 10 * privileged_user_flag
  +  5 * repeat_access_flag             -- any single user >= 5 hits
```
`gold_findings` grain: one row per suspicious domain, all component columns, an `evidence` struct (user/event samples), `intel_sources`. Emits the report-only metric (Section 5.4 AP3).

### 7.3 Report extraction, classical + AI (`pipelines/stream/extract_reports.py`)
Two passes over the same reports, and the point is the contrast.
1. **Classical pass** (`pipelines/classical/ioc_regex.py`): run `iocextract` over `bronze_reports` to pull well-formed and defanged indicators deterministically into `silver_iocs_regex` (`report_id, indicator_value, indicator_type, method='regex'`). Cheap, auditable, free, no model call.
2. **AI pass**: parse with Document Intelligence SQL functions (GA), then run structured extraction via the Agent Bricks Information Extraction agent (Section 8.2) into `silver_report_entities` and `silver_report_summaries` using the Section 5.8 schema. Catches what regex structurally cannot: prose-described indicators, misspelled/obfuscated ones, TTPs, targeted brands, recommended detections.
Merge extracted IOCs into `silver_iocs` with `source_name` set per method (`report_regex` or `report_ai_extraction`), `source_confidence` 55/60 respectively, `report_id` lineage. Defensive parsing (null-safe, retry note). Eval scores AI recall against `gt_report_entities` as a soft check (warn below 0.85).

### 7.4 Classical enrichment features (`pipelines/classical/`)
The deterministic feature layer that feeds both the score and the AI reasoning. No external APIs; all lookups resolve against generator-provided reference tables (`ref_ioc_enrichment`, `ref_brand_assets`), which stand in for WHOIS/passive-DNS/ASN services (say so, and put the real connectors on the roadmap slide).
- `feed_parse.py`: STIX 2.1 (`stix2`), MISP JSON (`pymisp`), and CSV feeds -> normalized `silver_iocs` with dedup (this is the classical ingestion the audience recognizes).
- `typosquat.py`: `tldextract` for registered-domain normalization plus `rapidfuzz` for brand-distance; emits `brand_similarity_score` and the nearest brand token. The similarity feature the score consumes and the graph reuses.
- `enrich_features.py`: joins registrar, ASN label, and resolved hosting IP from `ref_ioc_enrichment` (registrar/ASN/passive-DNS-style features); emits `is_recent_registration`, `shared_hosting_flag`, and `asn_reputation_bucket`.
Every feature here is either consumed by the Section 7.2 risk score or supplied to the AI enrichment prompt as structured context. If a feature is neither, cut it (Section 0 rule: classical technique must produce a score feature or a contrast moment).

### 7.5 Extraction diff (`pipelines/stream/extraction_diff.py`)
Builds the Act 1 contrast table: for each report, `regex_only`, `ai_only`, and `both` indicator sets, plus the AI-only entity types (TTPs, brands, kits) regex cannot produce. The hero report set makes it vivid: regex gets the clean domains, the agent additionally gets the defanged and the prose-described ones. Honest takeaway rendered as a caption: use both, regex as the cheap deterministic pass, AI for what regex cannot reach. This is what justifies the deterministic pre-filter in the router (Section 8.4).

---

## 8. Layer 4: Agent plane

### 8.1 Triage agent (`agents/triage_agent/`)
Built on Agent Bricks. Harness choice is open (Agent Bricks supports LangGraph, CrewAI, Agno, the Claude Code SDK, OpenAI Agent SDKs); pick one and record it. Single agent, not a multi-agent supervisor (debuggable on demo morning; MAS goes on the growth slide). Trigger: when a `gold_findings` row crosses the risk threshold during replay, FastAPI (or a Lakeflow hook) invokes the agent with the finding id. The agent runs its tool loop, writes a grounded brief and a recommended action with an action tier and its own confidence into `triage_queue` with `status=pending_review`, and its full trace to MLflow 3. Model served via FMAPI through AI Gateway; Databricks Sandbox for any code execution (backtests).

Brief prompt constraints **[exact intent]**: (a) introduce no facts absent from the evidence tools' output; (b) all indicators defanged; (c) sections: What happened, Who is affected, Evidence, Recommended action, Confidence; (d) cite any case-memory precedent by id.

### 8.2 Extraction agent (`agents/extraction_agent/`)
Agent Bricks Information Extraction agent over the Section 5.8 schema. Called by `extract_reports.py`. Deterministic-enough for the anti-join reveal; eval covers recall.

### 8.3 Tools (`agents/tools/`, exposed over MCP as UC functions)
- `query_telemetry(domain)` -> dns/proxy/email hits (counts + samples).
- `check_auth_anomalies(employee_ids[])` -> geo mismatches, failed-login bursts, lockouts, timing vs clicks.
- `get_user_context(employee_ids[])` -> department, is_privileged, is_vip, groups.
- `get_campaign_cluster(domain)` -> cluster id/name and shared-infra evidence.
- `lookup_policy(domain, action)` -> tier, auto_threshold, allowlist hit.
- `search_case_memory(finding_signature)` -> prior adjudicated cases (id, verdict, reason_code, excerpt).
- `get_report_context(domain)` -> matching rows from `silver_report_entities`/`silver_report_summaries` (structured lookup over already-extracted content; no Vector Search index needed, since Layer 3 extraction already turned the reports into queryable tables).
- A curated Genie space for ad-hoc hunting (used in Act 3 for the audience question). Register it as a tool and as a trusted-question set.

### 8.4 Policy router (`agents/router/policy_router.py`)
Reads `policy_store` (versioned). Routes on confidence AND blast radius, not confidence alone. Composite confidence = deterministic components dominant (exact IOC match, risk score, brand similarity) with the model's self-reported confidence a minor input; the groundedness judge (Section 10) must pass before any auto-execute.

Tier matrix seeded in policy_store **[exact]**:

| Tier | Actions | Auto-execute rule |
|---|---|---|
| 0 | close-as-benign, merge-duplicate, add-to-watchlist, enrich | auto if composite >= threshold |
| 1 | block-domain-at-proxy | auto only if exact high-confidence IOC match; notify + reversible (rollback token) |
| 2 | password-reset, account-disable (anything touching identity) | never auto; always human queue, any confidence |

Allowlist check precedes tiering: an allowlisted domain closes as benign citing the allowlist entry. This is how the clubcard-autumn sibling auto-closes after the summer exception is recorded.

### 8.5 Gateway (Unity AI Gateway)
All model traffic (pipeline `ai_query` and agent turns) egresses through AI Gateway: guardrails, per-workload budgets, usage tracking, provider fallback. Model choice is a live demo point (FMAPI exposes OpenAI, Anthropic, Gemini, Qwen, Kimi, Grok under one governance surface); the enrichment model can be flipped live to show cost/quality tradeoffs. Managed Omnigent (beta) appears on one forward slide as out-of-prompt enforcement of the tier-2 human gate; the Lakebase router is the primary, GA-safe gate.

---

## 9. Layer 1: Databricks App (React + FastAPI)

### 9.1 Views (React, `app/frontend/src/views/`)
1. **Director Console:** Run, Pause, Speed slider, Inject buttons (one per attack path: AP1..AP5), Inject-sibling (clubcard-autumn), plus fallback controls (Section 12.6): Fire-agent-manually, Load-precomputed-brief, Skip-to-T-1. Shows sim clock and running state.
2. **Live Triage Board:** stream of findings with risk score climbing live (SSE), the hero highlighted, campaign tags, source badges. This is the Act-2 centerpiece.
3. **Approval Queue:** each item shows the agent brief, evidence, recommended action + tier, agent confidence, judge groundedness, and Approve/Reject with a reason-code selector (Section 6.1). Captures OBO identity on action.
4. **Metrics Strip:** counters (auto-resolved, auto-executed, queued), agent-human agreement rate, escalation rate, tokens/cost via gateway. Feeds off Unity Catalog Metrics / AI/BI where possible.

### 9.2 Backend (FastAPI, `app/backend/`)
Serves the built React bundle and the API. Authenticates as the App service principal for system actions; captures OBO user identity on approve/reject and stamps `resolver_identity`. Talks to Lakebase for hot reads/writes and triggers the replay Job and agent invocations.

### 9.3 SSE (`app/backend/sse.py`, `app/frontend/src/sse.ts`)
One SSE stream (`GET /api/stream`) multiplexing typed events. Event types **[exact names]**:
- `replay.tick` `{sim_clock, speed, running, ingested_since_last: {dns, proxy, email, auth}}`
- `finding.updated` `{finding_id, domain, risk_score, components, status}`
- `agent.started` `{finding_id, agent_run_id}`
- `agent.step` `{agent_run_id, tool}`
- `agent.completed` `{agent_run_id, finding_id, brief_excerpt, recommended_action, tier, confidence, groundedness}`
- `decision.routed` `{decision_id, finding_id, route, tier, action}`
- `queue.updated` `{queue_id, status}`
- `metrics.updated` `{auto_resolved, auto_executed, queued, agreement_rate, escalation_rate, tokens}`

Two simplifications from an earlier draft, both deliberate. First, there is no per-row `event.ingested` type: at replay speed a single act can generate thousands of telemetry rows, and pushing one SSE message per row risks flooding the stream and the React render loop for a payoff (a tick mark per event) the aggregate counts on `replay.tick` already deliver. Second, `agent.step` carries only the tool name, not `input_summary`/`output_summary`: streaming full tool detail live duplicates `GET /api/agent/traces/{finding_id}`, which already exists for pulling the complete trace once `agent.completed` fires. The Triage Board shows lightweight "querying telemetry... checking auth anomalies..." steps live; the full inspectable trace renders on completion, which is when the audience actually wants to read it, not mid-stream.

Use `sse-starlette`. Reconnect-safe (Last-Event-ID). Do not use WebSockets (SSE is more reliable through the Apps proxy).

### 9.4 Endpoints (`app/backend/routes/`) [exact paths]
- `POST /api/replay/start` `{scenario, speed}`
- `POST /api/replay/inject` `{path_id}`
- `POST /api/replay/pause`
- `POST /api/replay/seek` `{to_ts}`
- `GET /api/findings`
- `GET /api/queue`, `GET /api/queue/{id}`
- `POST /api/queue/{id}/approve` `{reason_code?, notes?}`
- `POST /api/queue/{id}/reject` `{reason_code, notes}`
- `POST /api/decisions/{id}/rollback`
- `GET /api/metrics`
- `GET /api/agent/traces/{finding_id}`
- `GET /api/stream` (SSE)

### 9.5 App config (`app/app.yaml`)
Declare the FastAPI entrypoint, the built frontend path, required Lakebase and warehouse resources, the service principal, and env for `catalog`, `llm_endpoint`, Job ids, and Genie space id. Note Context-Based Ingress as optional for external audience access.

### 9.6 Contract tests (`app/tests/test_contract.py`)
Against a running Lakebase: start replay advances `replay_state`; a finding crossing threshold creates a queue item; approve/reject writes a feedback record with the right reason code and stamps identity; rollback marks the decision reversed; the SSE stream emits each event type at least once during a scripted replay.

---

## 10. Layer 5: Feedback and evaluation

### 10.1 Feedback taxonomy (`agents/eval/reason_codes.py`)
Both lanes produce feedback. Human lane: reason-coded verdict from the Approval Queue. Auto lane: every auto-resolution scored against `gt_filler_labels` / ground truth after the fact (proxy for delayed investigation outcomes in production). The reason code routes the feedback:
- `wrong_classification` -> eval dataset + case memory (agent got the verdict wrong).
- `insufficient_evidence` -> eval dataset (tighten tool use / prompt).
- `wrong_action` -> eval dataset + policy review.
- `policy_exception` -> allowlist + policy_store, NOT agent memory (agent reasoned correctly on the info it had).
Only reason-coded, confirmed decisions enter case memory; ambiguous ones stay eval-only. State this on stage; humans mislabel too.

### 10.2 Judges (`agents/eval/judges.py`)
Two MLflow 3 judges, but only one gates anything live. The groundedness judge (brief claims must trace to evidence-tool output) is the sole live gate: it must pass before any auto-execute, and its score shows live in the Approval Queue. The action-appropriateness judge (recommended tier matches blast radius) runs offline as part of the nightly eval build (Section 10.3) and is tracked as a metric, not wired to block anything live. Two live-gating judges is one more live-path dependency than the demo needs; the trust story ("why should I believe this brief") rests entirely on groundedness, and action-appropriateness is exactly the kind of thing that's more honestly measured in aggregate over the eval set than asserted per-decision on stage.

### 10.3 Eval dataset + optimization (`pipelines/eval/`)
`build_eval_dataset.py`: feedback records + traces become a versioned MLflow eval dataset that grows by itself. `optimize_agent.py`: the Agent Bricks evaluation-and-optimization loop produces agent v2 from accumulated disagreements, compared against v1 on the grown eval set. Do NOT run the optimizer live; pre-bake the v1-vs-v2 MLflow comparison (auto-close precision up, escalation rate down, agreement rate up) and render it in Act 4. Promotion is a serving-endpoint traffic split (shadow, then promote); show shadow mode as the CI/CD-for-agents framing.

**Risk flag:** this is the single highest platform-API risk item in the whole build. Agent Bricks' optimization loop is the newest capability in this plan (expanded at DAIS 2026, weeks before this build), so its invocation pattern is the least likely to be stable, well-documented, or bug-free. Budget real debugging time for it, do not leave it to the last day, and if it proves unstable to wire correctly with the time available, fall back to a clearly-labeled illustrative comparison (a hand-authored but plausible v1-vs-v2 chart, explicitly noted as illustrative in `BUILD_NOTES.md`) rather than blocking the whole build on a brand-new API. The rest of the demo does not depend on this succeeding; only Act 4's batch-improvement reveal does, and that reveal already has the live retrieval-learning beat (Section 10.5, item 1) as its stronger, lower-risk sibling.

### 10.4 Monitoring
Lakehouse Monitoring on the decision and feedback Delta mirrors; an escalation-rate spike is the earliest drift alarm. One roadmap line.

### 10.5 The learning beats (scripted, deterministic, rehearsable)
1. **Live retrieval learning (Act 4):** inject `clubcard-summer-deals[.]com`; agent escalates recommending a block; presenter rejects with `policy_exception` ("known vendor"); a versioned allowlist entry lands in policy_store; presenter injects `clubcard-autumn-deals[.]com`; it auto-closes citing the adjudicated case by id.
2. **Batch improvement reveal (Act 4):** the pre-baked v1-vs-v2 MLflow experiment, with the metrics strip showing agreement rate trending up.

---

## 11. Detection export and campaign graph

### 11.1 Sigma export (`pipelines/detections/sigma_export.py`)
Generate two Sigma rules as Python dicts from a finding: (a) proxy rule, URI contains the FreshCart kit path `/wp-login-secure/`; (b) DNS rule, query in the top-N campaign domains. Fields: `title, id (uuid5 from content), status: experimental, tags` (MITRE), `falsepositives, level`. Serialize to YAML, validate via pySigma `SigmaCollection`, convert to SPL via `pysigma-backend-splunk`, write `.yml`/`.spl` to the Git folder and record in `detections`. Backtest against 30 days of bronze: hits, FP rate vs known-benign, recall vs ground truth; only a passing rule is proposed. A scheduled Job runs approved rules as detections. Facilitator note: Databricks acquired SPL's creator (SiftD.ai); detections-as-code is the workflow.

### 11.2 Threshold backtesting (supports the routing-credibility beat)
Because ground truth is known, simulate the policy against 30 days: at threshold 0.85, count wrong auto-closes, escalations, and analyst-hours cleared. Render as a small table/chart in the Metrics Strip or a notebook the presenter can show. Makes the threshold a measured choice, not a vibe.

### 11.3 Campaign graph (`pipelines/graph/campaign_graph.py`)
Edges from `silver_iocs` + `ref_ioc_enrichment`: shared hosting_ip, shared registrant_email, shared kit_id, co-mention in a report. `greedy_modularity_communities`; keep communities >= 10 nodes; label by majority `gt_campaigns`. Matplotlib spring layout, communities colored, hero starred. Print "455 indicators -> 3 campaigns + noise". Instructor demo, pre-built.

---

## 12. Demo runbook (`RUNBOOK.md`)

### 12.1 Arc
Four acts on the autonomy ladder: manual hunt, AI-assisted enrichment, agentic investigation with human approval, agent-authored detections backtested before review.

### 12.2 Act 1, The advisory drops (~20 min)
Open on the classical foundation the room knows: STIX/MISP/CSV feeds parsed into one governed `silver_iocs` table, typosquat distance and registrar/ASN features attached. Then the blend beat: run the regex-vs-agent extraction diff (Section 7.5) on the FreshCart reports, showing regex catching the clean indicators and the agent additionally catching the defanged and prose-described ones plus TTPs. State the takeaway (use both; regex cheap and deterministic, AI for what it cannot reach). Then drop R14 into the Volume live; extraction turns it into rows; the anti-join reveals `tesco-parcel-tracking[.]net` is in no feed; a hunt join finds 2 internal DNS hits from 4 days ago. Introduce bronze/silver/gold, Unity Catalog, FMAPI while doing the work. Payoff: classical and AI on the same task, then intel to internal exposure in a few statements.

### 12.3 Act 2, The attack replays live (~20 min, centerpiece)
Click Run. 72 simulated hours in ~6 minutes stream into bronze; Lakeflow enriches and scores continuously; the Triage Board shows the hero domain's risk climbing ~40 to ~87 as each signal lands; Priya's compromise assembles on screen. The "one platform" argument made visceral.

### 12.4 Act 3, Agentic investigation + audience question (~25 min)
The hero finding crosses threshold; the triage agent fires automatically; its tool loop and MLflow trace render live; it writes a grounded brief and queues a tier-2 password-reset for Priya, which the presenter approves (OBO identity stamped). Then take a question from the room into the Genie space ("which privileged users touched anything similar to a Tesco domain this week?") answered live. Close with the judge score: why the brief is trustworthy.

### 12.5 Act 4, Close the loop (~15 min)
The learning beats (Section 10.5): policy-exception rejection creates an allowlist entry, the sibling auto-closes from memory; the pre-baked v1-vs-v2 improvement reveal. Then Sigma export to Git to a scheduled detection Job firing against replay data; the campaign graph (455 -> 3). End on the architecture diagram they now understand and the production path. One honest closing mention of Lakewatch as the productized direction; the demo ran on GA primitives.

### 12.6 Fallbacks (director-console buttons + pre-baked assets)
- Replay stalls -> Skip-to-T-1 (two-second jump).
- Agent endpoint hiccups -> Load-precomputed-brief for the hero.
- Auto-trigger misfires -> Fire-agent-manually.
- Genie question risky -> fall back to a rehearsed trusted question.
- Any live model call fails -> the metrics strip and boards keep running on synced state.
Cut order if behind: audience Genie question becomes a rehearsed one; graph shrinks to 2 minutes; dashboard becomes a screenshot. Never cut Act 2's climbing score or Act 3's agent trace + approval.

### 12.7 Pre-flight checklist
Run `00_load_world` and `99_validate`; dry-run the full replay; confirm the agent endpoint responds and the trace renders; seed policy_store; assemble/screenshot the metrics dashboard; verify the Git folder and detection Job; rehearse the audience Genie question; confirm OBO identity stamping.

---

## 13. Validation and definition of done

### 13.1 `pipelines/99_validate.py` (hard asserts)
Row counts per table within +/-2%. All named domains from 5.2 exist in their specified sources; feed-gap domain absent from all structured feeds and present in `bronze_dns_logs` with exactly 2 distinct employees. AP1 invariants: 17 distinct clickers, 3 credential POSTs, 3 failed-login bursts in the 20-45 min window, Priya's RO success event, Priya `is_privileged`. AP2/AP4/AP5 and both counterexamples per 5.4. Filler pool: every `gt_filler_labels` row routes to its expected lane through `policy_router`. Graph pre-check: 3 communities >= 10 nodes, each labeled by its majority campaign. Reference outputs exist and `gold_findings_ref` rank order matches `gt_expected_findings` (hero #1; ranks 2-5 may permute within tolerance). Policy beat: after recording the summer allowlist entry, the autumn sibling routes to auto-close.
Classical layer: `silver_iocs_regex` non-empty for the FreshCart reports; the extraction diff yields a non-empty `ai_only` set for at least one report where the agent recovers a defanged or prose-described indicator regex missed; typosquat feature present with the hero domain `brand_similarity_score >= 85`; enrichment features (`is_recent_registration`, `shared_hosting_flag`, `asn_reputation_bucket`) populated for clusters A-D and null for noise.
Soft (warn): extraction recall vs `gt_report_entities` >= 0.85; full replay under target wall time.

### 13.2 Definition of done
- [ ] `pytest datagen/tests` green locally.
- [ ] `00_load_world` then `99_validate` pass in-workspace with zero manual edits.
- [ ] Lakebase schema applies; policy_store seeded; synced tables readable.
- [ ] Lakeflow replay of AP1 yields the hero finding at expected score.
- [ ] Triage agent runs its full tool loop on the hero and writes a grounded brief; router queues the tier-2 action.
- [ ] FastAPI contract tests pass; SSE emits every event type during a scripted replay.
- [ ] All four React views render live; director console drives the replay; fallback buttons work.
- [ ] A rejection writes a feedback record + case-memory entry; the autumn sibling auto-closes from memory.
- [ ] Pre-baked v1-vs-v2 MLflow experiment renders.
- [ ] Sigma rules validate through pySigma; a Job runs them; graph yields 3 labeled communities.
- [ ] Every indicator in UI, briefs, reports, README is defanged.
- [ ] No em dashes, no banned vocabulary anywhere (grep passes).
- [ ] `requirements.txt` pinned; `BUILD_NOTES.md` records deviations and status caveats.

---

## 14. Content and prose style guide (all generated text)

Applies to agent briefs, report content, UI copy, and every markdown cell.
- Direct, declarative sentences. No em dashes anywhere; use commas, colons, or split the sentence.
- Banned vocabulary: delve, leverage (as a verb), seamless, robust, cutting-edge, revolutionize, harness, unlock, empower, journey, "it's not just X, it's Y".
- Concept explanations (for the platform-new audience): at most 6 sentences, ending with the CTI job it serves. Explain thoroughly on first mention: Unity Catalog objects, Delta (transactions, schema enforcement, time travel), medallion, FMAPI and `ai_query` (models run where data lives, governed, nothing leaves), serverless, Lakebase, AI Gateway, Agent Bricks, MLflow tracing, AI/BI. Do NOT explain: IOC, TTP, phishing, MITRE, STIX/MISP, Sigma's purpose.
- Synthetic reports may use vendor-blog tone but stay competent, not parody, and stay defanged.
- Status honesty in any presenter-facing note: mark preview/beta features as such per Section 4.3.

---

## 15. Manual configuration checklist (UI vs code)

Claude Code writes all code (datagen, pipelines, agent tools, router, judges, FastAPI, React, Sigma, graph, SQL). These steps are Databricks configuration the instructor performs and the plan must document in README:
- Provision the FMAPI pay-per-token endpoint(s) and note the name in `llm_endpoint`.
- Register the Agent Bricks triage and extraction agents from `agents/` configs; wire the MCP tools (UC functions).
- Create and curate the Genie space (table descriptions, synonyms, three trusted questions).
- Configure Unity AI Gateway routes, budgets, and guardrails for the endpoints.
- Set up the Git folder for detections and the scheduled detection Job.
- Assemble the AI/BI dashboard / Unity Catalog Metrics for the Metrics Strip and screenshot it.
- Deploy the Databricks App and (optionally) configure Context-Based Ingress for external access.
- Configure Lakebase synced tables per `sync_config.py`.
Record any version-specific deviation from documented behavior in `BUILD_NOTES.md`.
