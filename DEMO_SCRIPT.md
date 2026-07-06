# FreshCart PhishOps Demo Script

## Purpose

This document is a detailed presenter script for the demo described in `PLAN.md`.

The audience assumption is beginner-friendly:

- They may not know cybersecurity terms.
- They may not know threat intelligence terms.
- They may not know Databricks.
- They should still understand what is happening, why it matters, and why each platform component exists.

The demo story is:

> A suspicious Tesco-themed phishing campaign appears. The lakehouse ingests intelligence and internal telemetry, scores exposure, starts an agentic investigation, routes risky actions to a human approval queue, learns from the human decision, and turns the investigation into future detections.

Working title on screen:

> FreshCart PhishOps: 72 hours on the lakehouse

One-line thesis:

> The platform detects, agents investigate and author, a human approves, and every decision becomes training data.

## Presenter Ground Rules

Use these rules throughout the demo.

- Speak slowly. Most concepts are new to the audience.
- Define a term the first time you say it.
- Keep every indicator defanged in speech, slides, UI, reports, and markdown. Say `tesco-clubcard-support dot com`, and show `tesco-clubcard-support[.]com`.
- Do not describe any preview feature as generally available. Context-Based Ingress is public preview. Managed Omnigent is beta. Lakehouse//RT and Lakewatch are preview or forward-looking in this demo.
- Do not claim that the system is making irreversible changes automatically. Identity actions always go to a human.
- Repeat the trust model often: deterministic evidence first, AI explanation second, human control for high-impact actions.
- If a live model call fails, continue from the synced state and use the fallback buttons.

## Glossary For The Presenter

Use this section as your private cheat sheet. You do not need to read it word for word, but you should be comfortable explaining each term simply.

Audience caution: the real Tesco audience is a security-engineering room with deep threat-intel knowledge. Do not read the cybersecurity or threat-intelligence definitions aloud on stage. Reading back IOC, TTP, phishing, MITRE, STIX, MISP, or Sigma to this room sounds condescending, and the plan style guide in Section 14 explicitly says not to explain them. Keep those two subsections private. Spend your stage explanation time on the Databricks concepts, which are new to this audience.

### Cybersecurity Basics

Presenter-only reference. Do not read aloud to the Tesco audience.

**SOC**

A Security Operations Center is the team and process that watches for cyber threats, investigates alerts, and coordinates response. In a large company, the SOC is the place where security signals from email, identity, network, cloud, and endpoint systems are triaged.

**Alert**

An alert is a signal that something might be wrong. Alerts can be true positives, false positives, or unclear cases. The hard part is not creating alerts. The hard part is knowing which alerts matter.

**Finding**

In this demo, a finding is a higher-quality security item created after the system combines raw telemetry, threat intelligence, scoring, and context. A finding is more useful than a raw alert because it contains evidence and a risk score.

**Incident**

An incident is a confirmed security event that needs a response. A finding becomes an incident only after investigation or policy says it should.

**Phishing**

Phishing is a social-engineering attack where an attacker tricks a person into clicking a link, opening an attachment, entering credentials, or taking another unsafe action. This demo focuses on phishing links that look related to Tesco loyalty rewards.

**Credential Harvesting**

Credential harvesting means tricking users into entering usernames, passwords, or tokens into a fake login page. The attacker then tries those credentials against real systems.

**BEC**

Business Email Compromise is a fraud pattern where attackers impersonate trusted business contacts, executives, suppliers, or finance teams. The goal is usually payment fraud, bank-detail changes, or invoice manipulation.

**Privileged User**

A privileged user has access that can cause more damage if compromised. Examples include cloud admins, domain admins, finance operations, and production support users. Priya Nair is privileged in this demo because she belongs to the `Cloud-Admins` group.

**Lockout**

A lockout happens when an account is temporarily blocked after too many failed login attempts. In this demo, lockouts after phishing clicks suggest that stolen credentials were tried by an attacker.

**Geo Anomaly**

A geo anomaly is a login from a location that does not fit the user's normal pattern. If a user usually logs in from India or the UK and suddenly logs in from Romania on an unknown device, the SOC should investigate.

**False Positive**

A false positive is something that looks bad but is actually safe. `clubcard-summer-deals[.]com` is the key false-positive teaching example in this demo. It looks phishy, but it belongs to Tesco's own marketing agency.

**False Negative**

A false negative is a real threat that the system misses. Act 1 shows how report extraction reduces this risk by finding `tesco-parcel-tracking[.]net`, which does not appear in structured feeds.

### Threat Intelligence Basics

Presenter-only reference. Do not read aloud to the Tesco audience.

**Threat Intelligence**

Threat intelligence is information about attackers, campaigns, infrastructure, techniques, and indicators. It helps defenders answer: what should we look for, how dangerous is it, and has it touched us?

**CTI**

CTI means Cyber Threat Intelligence. CTI turns external knowledge about threats into internal security action.

**Indicator**

An indicator is a clue that may point to malicious activity. Examples include a domain, URL, IP address, sender email, file hash, phishing kit path, or user-agent string.

**IOC**

IOC means Indicator of Compromise. It is a specific indicator that may show compromise or attempted compromise. In this demo, examples include `tesco-clubcard-support[.]com`, suspicious sender emails, IP addresses, and phishing paths like `/wp-login-secure/`.

**TTP**

TTP means Tactics, Techniques, and Procedures. It describes attacker behavior, not just individual indicators. An IOC might be one suspicious domain. A TTP might be credential phishing through a fake rewards login page.

**MITRE ATT&CK**

MITRE ATT&CK is a public knowledge base of attacker techniques. It gives defenders a shared language. In this demo, FreshCart uses `T1566.002`, which maps to phishing through a link.

**STIX**

STIX is a structured format for sharing threat intelligence. Think of it as JSON for threat intel objects such as indicators, campaigns, and relationships.

**MISP**

MISP is an open-source threat intelligence sharing platform and format. Security teams use it to share indicators and context.

**Sigma**

Sigma is a vendor-neutral format for detection rules. A Sigma rule can later be converted into a search for a specific security tool. In this demo, the system generates Sigma from a finding, backtests it, and writes it to Git.

**Defanging**

Defanging makes indicators safe to display or copy. For example, say `tesco-clubcard-support dot com` out loud and show `tesco-clubcard-support[.]com` on screen. This prevents accidental clicks and makes it clear that the string is dangerous or suspicious.

**Typosquatting**

Typosquatting is when attackers register domains that look like a real brand. For example, a fake rewards domain may look close to a real Tesco domain. The demo calculates brand similarity to help detect this.

**Campaign**

A campaign is a related set of attacker activity. FreshCart PhishOps is one campaign in this demo. It has shared domains, hosting, kit fingerprints, and reports.

**Kit Fingerprint**

A phishing kit is reusable attacker code for fake login pages. A kit fingerprint is a clue that multiple domains may be operated by the same attacker. In this demo, FreshCart uses `fc-kit-v3`.

### Databricks And Data Platform Basics

These are the concepts to explain on stage. This audience knows security but is new to Databricks. Explain each thoroughly on first mention, and end each explanation with the security job it serves.

**Lakehouse**

A lakehouse combines the flexibility of a data lake with the reliability and governance of a data warehouse. In this demo, security data, threat intel, agent traces, decisions, and feedback all live in one governed system.

**Unity Catalog**

Unity Catalog is Databricks governance for data and AI assets. It controls permissions, lineage, discovery, and audit. In the demo, it governs tables, functions, volumes, models, and app access.

**Delta**

Delta is the storage format used for reliable lakehouse tables. It supports transactions, schema enforcement, and time travel. That means security tables can be updated safely and audited.

**Bronze, Silver, Gold**

This is the medallion pattern. Bronze is raw data, close to how it arrived. Silver is cleaned and normalized data. Gold is business-ready or analyst-ready data. In this demo, raw DNS, proxy, email, and auth logs start in bronze. Cleaned indicators and reports become silver. Risk-scored findings become gold.

**Lakeflow**

Lakeflow is the streaming and pipeline layer. In this demo, it continuously processes replayed events, joins them with threat intelligence, enriches them, scores them, and writes findings.

**FMAPI**

FMAPI means Foundation Model APIs. It lets Databricks call foundation models through governed endpoints. In this demo, models summarize and classify suspicious evidence, but the raw evidence stays governed.

**`ai_query`**

`ai_query` is a Databricks SQL function that calls an AI model from SQL. In this demo, it enriches suspicious domains using structured features.

**Agent Bricks**

Agent Bricks is the Databricks agent platform used here for the triage agent and extraction agent. The agent does not just produce text. It calls tools, checks evidence, writes a brief, records traces, and learns from feedback.

**MCP Tool**

MCP means Model Context Protocol. In simple terms, it is a standard way for an agent to call tools. In this demo, the agent can query telemetry, check auth anomalies, get user context, look up policy, and search case memory.

**Serverless**

Serverless means you do not manage or pre-size the machines. The platform starts compute when work arrives and scales it for you. In this demo, serverless notebooks, serverless SQL, the Databricks App, and Lakebase all run this way, so the SOC console can handle a room of viewers without capacity planning.

**Lakebase**

Lakebase is serverless Postgres inside Databricks. It holds operational state for the app, such as the triage queue, approvals, decisions, policies, and replay state. It gives the UI fast reads and writes.

**Databricks App**

A Databricks App is a serverless app hosted in the workspace. This demo uses a React frontend and FastAPI backend to show the SOC console.

**SSE**

SSE means Server-Sent Events. It is a simple way for the backend to stream live updates to the browser. In this demo, SSE updates the triage board, queue, replay clock, and metrics.

**AI Gateway**

Unity AI Gateway governs model traffic. It handles guardrails, budgets, usage tracking, and fallback routing. This helps make AI usage observable and controlled.

**MLflow Tracing**

MLflow tracing records what the agent did: inputs, tool calls, outputs, timing, and scores. In this demo, the trace is the proof that the agent's brief is grounded in evidence.

**AI/BI**

AI/BI is the Databricks analytics and dashboard layer, including AI/BI dashboards and Unity Catalog Metrics. In this demo, it is the source behind the Metrics Strip: auto-resolved counts, agreement rate, escalation rate, and gateway token and cost figures.

**Genie**

Genie lets users ask natural-language questions over governed data. In this demo, the presenter asks a rehearsed SOC hunting question, and Genie answers from the trusted tables.

**OBO Identity**

OBO means on behalf of user. The app can perform system actions with its service principal, but approvals record the real human identity. This matters for audit.

## Demo Setup

### Required Screens

Prepare these screens before presenting:

1. Architecture diagram, platform estate.
2. Architecture diagram, runtime flow.
3. Databricks App, Director Console.
4. Databricks App, Live Triage Board.
5. Databricks App, Approval Queue.
6. Databricks App, Metrics Strip.
7. MLflow trace view.
8. Optional notebook or dashboard for extraction diff.
9. Optional Git folder for Sigma export.
10. Optional campaign graph image.

### Main Demo Objects

Use these names consistently:

- Campaign: FreshCart PhishOps
- Hero domain: `tesco-clubcard-support[.]com`
- Hero victim: Priya Nair
- BEC victim: Mark Whitfield
- Repeat visitor: Sophie Clarke
- Feed-gap domain: `tesco-parcel-tracking[.]net`
- False-positive domain: `clubcard-summer-deals[.]com`
- Learned sibling domain: `clubcard-autumn-deals[.]com`
- Benign lookalike: `tesco-fans-forum[.]com`
- High-confidence but low-exposure counterexample: `tesco-careers-verify[.]com`

### Attack Path Reference

Use this section when rehearsing. These are the five planted storylines that make the demo deterministic.

**AP1, the hero**

- Domain: `tesco-clubcard-support[.]com`
- Campaign: FreshCart PhishOps
- Theme: Clubcard rewards credential phishing
- Human story: employees receive a rewards email saying their Clubcard points expire soon
- Key victim: Priya Nair, a privileged cloud platform engineer
- Evidence sequence: email wave to 60 employees, 17 distinct clickers, 3 credential submissions, failed-login bursts, lockout, Priya successful login from Romania on unknown device
- Expected rank: number 1 in gold findings
- Teaching point: risk becomes serious when threat intelligence, exposure, credential entry, auth anomaly, and privileged-user context line up

**AP2, the finance fraud path**

- Domain: `tesco-supplier-billing[.]com`
- Campaign: SupplierPay
- Theme: supplier invoice or payment fraud
- Key victim: Mark Whitfield, accounts payable analyst (deliberately not privileged, so AP1 stays the only privileged-user finding in the top five)
- Evidence sequence: invoice-themed email, click, proxy POST, anomalous login from Romania
- Expected rank: number 2
- Teaching point: business email compromise is not always about malware. It is often about trust, finance process, and identity compromise

**AP3, the feed gap**

- Domain: `tesco-parcel-tracking[.]net`
- Source: report-only intelligence from R14
- Evidence sequence: report extraction finds it, structured feeds do not contain it, internal DNS shows 2 employees touched it
- Teaching point: if the SOC only reads structured feeds, it misses useful intelligence hidden in prose

**AP4, the fresh domain**

- Domain: `tescobank-secure-auth[.]com`
- Theme: recent bank-themed credential phishing
- Evidence sequence: fresh first-seen time, a few DNS hits, no credential entry, no auth anomaly
- Expected rank: number 3, because high recency lifts it despite modest exposure
- Teaching point: recency matters, but it does not automatically outrank stronger compromise evidence

**AP5, the repeat visitor**

- Domain: `tesco-rewards-login[.]com`
- Key victim: Sophie Clarke
- Evidence sequence: 9 visits across three days, no failed logins
- Expected rank: number 4 or number 5, because the repeat-access flag fires
- Teaching point: repeated access is suspicious, but lower priority than credential entry plus privileged-user compromise

### Risk Score Reference

Use this when explaining why the board ranking changes.

Exact starting weights, out of 100, from Section 7.2 of the plan. Keep these on one backup slide for a technical room. You do not need to read the numbers aloud, but be ready if asked.

- Source confidence: 25 points, scaled by max source confidence
- Distinct users hit: 20 points, scaled by distinct users up to 10
- Recency: 15 points, decaying with days since first seen
- Brand similarity: 15 points, scaled by brand similarity
- Credential entry flag: 10 points, any POST to a kit path
- Privileged user flag: 10 points
- Repeat access flag: 5 points, any single user with 5 or more hits

The design intent: the score is transparent and additive, so an analyst can read why a domain ranks where it does. No single component can carry a domain to the top on its own.

**Source confidence**

External feeds or reports say how suspicious an indicator is. This is useful, but it is only one input.

**Distinct users hit**

If one user touches a suspicious domain, it may be isolated. If many users touch it, the campaign has internal reach.

**Recency**

Fresh activity is more urgent than old activity. A domain first seen yesterday deserves attention because the attack may still be active.

**Brand similarity**

Domains that look like Tesco or Clubcard assets can trick users. Similarity increases suspicion, but similarity alone is not proof.

**Credential entry flag**

A POST to a phishing-style path means someone may have submitted credentials. This is much stronger than a simple page view.

**Privileged user flag**

If a cloud admin, domain admin, or payments operator is affected, impact rises.

**Repeat access flag**

Repeated visits from one user can mean a bookmark, repeated lure, or repeated interaction. It is useful supporting evidence.

### Routing Reference

Use this when explaining why some actions are automatic and others are human-gated.

**Tier 0**

Low-impact actions such as closing benign duplicates, adding to a watchlist, or enriching evidence. These can auto-execute when confidence is high enough.

**Tier 1**

Reversible containment actions such as blocking a domain at the proxy. These can auto-execute only under stricter rules, such as exact high-confidence IOC match.

**Tier 2**

Identity actions such as password reset or account disable. These never auto-execute in the demo. They always go to the human approval queue.

### Demo Timing

Total target duration: 90 minutes. The four acts are about 80 minutes; opening and closing add 10.

- Opening: 5 minutes
- Act 1, The advisory drops: 20 minutes
- Act 2, The attack replays live: 20 minutes
- Act 3, Agentic investigation and audience question: 25 minutes
- Act 4, Close the loop: 15 minutes
- Closing: 5 minutes

If you only have 45 minutes:

- Opening: 3 minutes
- Act 1: 10 minutes
- Act 2: 12 minutes
- Act 3: 15 minutes
- Act 4: 5 minutes

Never cut the risk score climbing in Act 2 or the agent trace and human approval in Act 3.

## Opening Script

### Slide: Title

Show:

> FreshCart PhishOps: 72 hours on the lakehouse

Say:

> Today I am going to show a security operations demo. I will assume no deep cybersecurity background, so I will define terms as we go.
>
> The story is a fake but realistic phishing campaign against a Tesco-like environment. The data is synthetic. The people are synthetic. The attacker infrastructure is synthetic. The workflow is real.
>
> The question we are answering is simple: if threat intelligence arrives, and employees start touching suspicious infrastructure, can one governed data and AI platform detect it, investigate it, route the right actions to humans, and learn from the decisions?

### Define The Core Problem

Say:

> A SOC team lives with too much noise. They receive threat feeds, advisories, reports, email logs, DNS logs, proxy logs, identity logs, and user reports. Most indicators never touch the company. Some touch the company but are harmless. A few matter a lot.
>
> The difficult job is to connect outside intelligence to inside exposure.
>
> In plain English: we do not only ask, "is this domain bad?" We ask, "did anyone in our company touch it, who touched it, what happened next, and what should we do?"

### Introduce The Demo Thesis

Say:

> This demo has four acts.
>
> First, we ingest threat intelligence and reports. Second, we replay an attack and score risk live. Third, an agent investigates and writes a grounded brief. Fourth, the human decision becomes feedback, memory, policy, and detection code.
>
> The important detail is that AI is not replacing evidence. Evidence comes first. The agent is a reasoning and explanation layer over governed data.

### Architecture Setup

Show the platform estate diagram.

Say:

> There are five layers.
>
> The top layer is the Databricks App, which is the SOC console. It has a Director Console, Triage Board, Approval Queue, and Metrics Strip.
>
> The operational layer is Lakebase. That is where the app keeps fast operational state: queues, decisions, feedback, policy, and replay state.
>
> The streaming intelligence layer is Lakeflow and Delta. That is where raw security events become scored findings.
>
> The agent layer is Agent Bricks. The agent calls tools, investigates evidence, writes a brief, and records a trace.
>
> The feedback layer is MLflow, evaluation datasets, case memory, and monitoring. This is how decisions improve the system over time.

### Explain Safety

Say:

> This is not a live attacker duel. Nothing generates malicious content live. All attacker data is pre-generated and replayed safely.
>
> Also, no high-impact identity action auto-executes. If the recommendation touches a user's account, it goes to a human approval queue.

## Act 1: The Advisory Drops

Target time: 20 minutes.

Goal: Show how external threat intelligence becomes internal exposure analysis.

### Act 1 Opening

Show the notebook, dashboard, or app section that displays structured feeds and reports.

Say:

> We begin the way many SOC workflows begin: outside intelligence arrives.
>
> Threat intelligence can arrive as structured feeds or unstructured reports. Structured feeds are machine-readable. Reports are human-readable. Both matter.

### Explain Structured Feeds

Show STIX, MISP, and CSV feed ingestion summary.

Say:

> Here we have three simple feed types.
>
> STIX is a structured threat intelligence format. MISP is a common threat-sharing format. CSV is the simplest possible feed format.
>
> These feeds contain indicators: domains, URLs, IP addresses, sender emails, and file hashes. The demo has 455 structured indicators. That sounds like a lot, but in real life the number can be much larger.
>
> Most of those indicators never appear inside our environment. That is normal. Threat feeds are broad. The SOC still needs to ask which indicators touched our company.

### Explain The Campaigns

Show the campaign list or summary.

Say:

> The synthetic world contains three attacker campaigns plus noise and decoys.
>
> FreshCart PhishOps is the hero campaign. It targets Clubcard-style rewards users with credential phishing.
>
> SupplierPay is a business email compromise theme against finance.
>
> CareerLure is fake recruitment activity.
>
> There is also unrelated noise and benign lookalikes. This matters because security systems must handle ambiguity, not just obvious evil.

### Explain Bronze, Silver, Gold

Show the medallion flow.

Say:

> Databricks often uses a medallion pattern: bronze, silver, and gold.
>
> Bronze is raw. Silver is cleaned and normalized. Gold is ready for analysts or applications.
>
> For this demo, raw DNS, proxy, email, and auth logs are bronze. Normalized indicators and extracted report entities are silver. Risk-scored security findings are gold.
>
> The SOC does not want to stare at raw rows forever. The SOC wants a small set of high-quality findings with evidence.

### Classical Parsing

Show `silver_iocs` or equivalent.

Say:

> First, the classical layer parses structured feeds.
>
> Classical means deterministic code, not AI. For example, parse STIX objects, parse MISP attributes, normalize domains, deduplicate repeated indicators, and attach feed confidence.
>
> This matters because deterministic parsing is cheap, auditable, and predictable. We should not use a model when a parser is the better tool.

### Explain Deduplication

Say:

> Deduplication means removing duplicate records that refer to the same thing.
>
> A domain may appear in two feeds with different confidence scores. Without deduplication, the system may double-count the same indicator and inflate risk.
>
> Here, feed overlap is intentional. It shows why threat intelligence needs data engineering, not just a folder of feeds.

### Explain Typosquatting And Brand Similarity

Show a typosquat score for `tesco-clubcard-support[.]com`.

Say:

> Attackers often use domains that look close to real brands. That is called typosquatting.
>
> The system compares suspicious domains against protected brand references: `tesco[.]com`, `tescobank[.]com`, `tescoplc[.]com`, `tescomobile[.]com`, `tesco[.]ie`, and tokens like `clubcard`.
>
> The hero domain, `tesco-clubcard-support[.]com`, is not owned by Tesco in this synthetic world, but it looks close enough to deserve attention.
>
> Similarity is not a verdict. It is one feature. We will later see benign domains that look similar too.

### Explain Unstructured Reports

Show a report sample.

Say:

> Structured feeds are only part of threat intelligence. Analysts also read reports, blog posts, advisories, DFIR writeups, social threads, and takedown emails.
>
> Reports are messy. Some indicators are defanged. Some are described in prose. Some mention attacker behavior without giving a clean indicator.
>
> This is where classical extraction and AI extraction complement each other.

### Regex Extraction

Show regex extraction output.

Say:

> The first pass is regex extraction. Regex means pattern matching.
>
> Regex is good at pulling obvious indicators from text. If a report contains a clean domain or IP address, regex can usually find it cheaply and deterministically.
>
> The limit is that regex does not understand meaning. It can miss defanged indicators, prose-described infrastructure, targeted brands, phishing kits, and MITRE techniques.

### Agent Extraction

Show extraction agent output.

Say:

> The second pass is an information extraction agent.
>
> The agent reads the same report and fills a structured schema: actors, indicators, techniques, targeted brands, phishing kits, confidence, summary, and recommended detections.
>
> The goal is not to let the model free-write a story. The goal is to convert messy text into governed rows that can be joined with internal telemetry.

### Extraction Diff

Show `regex_only`, `ai_only`, and `both`.

Say:

> This table compares what regex found, what the agent found, and what both found.
>
> The honest takeaway is not "AI replaces regex." The takeaway is "use both." Regex is cheap and deterministic. AI helps with the parts that require language understanding.
>
> This is a recurring pattern in the demo: deterministic systems produce evidence, AI adds interpretation, and policy controls action.

### Feed Gap Reveal

Drop or show R14, then show the extracted `tesco-parcel-tracking[.]net`.

Say:

> Now we have an important teaching moment.
>
> This report mentions `tesco-parcel-tracking[.]net`. That domain is not in any structured feed.
>
> If we only trusted feeds, we would miss it. After report extraction, it becomes a row in our silver intelligence table.

Run or show the anti-join: report-extracted indicators that are absent from structured feeds.

Say:

> This anti-join asks: which indicators came from reports but were not in any feed?
>
> We get one important result: `tesco-parcel-tracking[.]net`.

Run or show internal exposure join.

Say:

> Now we ask the SOC question: did anyone inside the company touch this?
>
> The answer is yes. Two employees queried it in DNS four days ago.
>
> This is the first payoff. We turned prose in a report into a governed indicator, joined it to internal telemetry, and found internal exposure.

### Act 1 Summary

Say:

> Act 1 was about building the evidence layer.
>
> We parsed structured feeds, extracted intelligence from unstructured reports, normalized indicators into silver tables, attached brand and infrastructure features, and found a feed gap that touched internal users.
>
> Nothing agentic has happened yet. That is intentional. Before agents investigate, the platform needs trustworthy data.

## Act 2: The Attack Replays Live

Target time: 20 minutes.

Goal: Show live risk scoring as internal telemetry arrives.

### Act 2 Opening

Switch to the Databricks App.

Show the Director Console and Live Triage Board.

Say:

> Act 2 is where the data starts moving.
>
> We will replay 72 simulated hours in about six wall-clock minutes. The replay writes synthetic DNS, proxy, email, and auth events into bronze Delta tables.
>
> Lakeflow processes those events continuously. As evidence accumulates, the risk score for suspicious domains changes live.

### Explain Telemetry

Say:

> Telemetry is machine-generated evidence about what happened.
>
> DNS logs show domain lookups. Proxy logs show web requests. Email events show delivery and clicks. Auth logs show login attempts, failures, lockouts, devices, and countries.
>
> A single log line is rarely enough. The important signal comes from correlation across sources.

### Explain The Replay

Point to the Director Console.

Say:

> The Director Console controls the replay. It can run, pause, speed up, inject specific attack paths, or jump to a known point if the live stream stalls.
>
> The attack paths are scripted. That gives us a live-feeling demo without live attacker risk.

Click `Run`.

Say:

> I am clicking Run now. Watch the triage board. The system is not waiting for the entire batch to finish. It scores as the stream advances.

### Explain The Risk Score

Show the score formula or component panel.

Say:

> The risk score is a weighted combination of evidence.
>
> Source confidence asks whether outside intelligence thinks the indicator is suspicious.
>
> Distinct users hit asks how many employees touched it.
>
> Recency asks how fresh the indicator is.
>
> Brand similarity asks whether the domain looks close to a protected brand.
>
> Credential entry asks whether someone posted data to a phishing-like page.
>
> Privileged user asks whether any affected user has sensitive access.
>
> Repeat access asks whether a user visited repeatedly.
>
> This is intentionally explainable. A security analyst should be able to see why the score moved.

Optional deeper explanation:

> Notice that the model is not the only source of truth. The score has transparent components. The AI enrichment can reason over those components, but the components themselves are visible.

### Early Stream: Low And Medium Findings

As lower-risk items appear, point to them.

Say:

> These early items are useful because they show that not everything becomes a major incident.
>
> Some indicators are known-bad but low impact inside our environment. Some are scanner noise. Some are benign duplicates. The system can close or route many of those before an analyst spends time.

### Teaching Counterexample: High Confidence Is Not Enough

Point to `tesco-careers-verify[.]com` if visible.

Say:

> Here is a good beginner lesson. `tesco-careers-verify[.]com` has high external confidence, but only one internal DNS hit from guest Wi-Fi.
>
> High feed confidence is not the same thing as high business risk.
>
> If nobody important touched it, and there is no credential entry or auth anomaly, it should not outrank a campaign that affected employees.

### Teaching Counterexample: Similarity Is Not Verdict

Point to `tesco-fans-forum[.]com` if visible.

Say:

> This domain looks Tesco-like, but the confidence is low and the visits are benign.
>
> Brand similarity is useful, but it is not a verdict. If we treated similarity alone as proof, we would create too many false positives.

### Hero Finding Starts Climbing

Point to `tesco-clubcard-support[.]com`.

Say:

> Now watch the hero domain: `tesco-clubcard-support[.]com`.
>
> At first, it has external intelligence and brand similarity, so it starts around a risk score of 40. That is suspicious, but not enough to tell the full story.
>
> As the replay advances, employees receive phishing emails, some click, some submit credentials, and then identity logs show failed login bursts. Watch the score climb toward the high 80s.

As the score rises, narrate each component.

Say:

> The score is climbing because distinct users are increasing.
>
> Now the proxy evidence shows POST requests to `/wp-login-secure/`, which looks like credential entry.
>
> Now identity evidence is joining in: failed logins after the clicks.
>
> Now Priya Nair appears, and she is privileged. That increases the impact.

### Explain Temporal Correlation

Say:

> Temporal correlation means events are suspicious because of their timing.
>
> A failed login by itself can be normal. A phishing click by itself might be a user mistake. A failed-login burst 20 to 45 minutes after a phishing click is stronger evidence.
>
> The system is connecting those events into one story.

### Explain Priya's Compromise

Show Priya's evidence.

Say:

> Priya Nair is a Senior Cloud Platform Engineer. She belongs to `Cloud-Admins`, so her account has higher impact.
>
> The system sees that she clicked the FreshCart domain, submitted credentials, had failed logins afterward, and then had a successful login from Romania on an unknown device.
>
> That does not prove every detail of attacker intent, but it is enough to escalate. The risk is no longer just a suspicious domain. It is a privileged-user compromise scenario.

### Explain Lakeflow

Say:

> Lakeflow is doing the continuous processing here.
>
> It reads new bronze events, normalizes them, joins them with silver threat intelligence, adds classical enrichment features, calls governed AI enrichment where needed, computes the risk score, and writes gold findings.
>
> The UI is reading those gold findings through Lakebase, so the board updates quickly.

### Explain Lakebase In The UI

Say:

> Lakebase is the operational database behind the SOC console.
>
> The lakehouse stores analytical history. Lakebase gives the app fast operational reads and writes for queues, decisions, replay state, and feedback.
>
> The important architecture idea is that the app and analytics are connected. The analyst's decision does not disappear into a separate ticket system. It becomes governed data.

### Act 2 Payoff

When the hero reaches top rank, say:

> This is the centerpiece of the demo.
>
> The system did not just say "this domain is bad." It showed why this domain matters to this company right now.
>
> Seventeen employees clicked. Three submitted credentials. Priya, a privileged user, had suspicious auth activity afterward. That is why `tesco-clubcard-support[.]com` is ranked number one.

### Show The Metrics Strip

Point to the Metrics Strip.

Say:

> While the stream ran, the Metrics Strip on the side was moving too.
>
> It shows auto-resolved, auto-executed, and queued counts, the agent-to-human agreement rate, the escalation rate, and the tokens and cost spent through the AI Gateway.
>
> This matters for two reasons. First, it shows the system is clearing low-value noise on its own, not just creating more alerts. Second, the token and cost line shows AI spend is governed and measured, not a mystery bill.
>
> These numbers come from the AI/BI analytics layer over the same governed tables, so the operations view and the analytics view agree.

### Act 2 Summary

Say:

> Act 2 showed the live detection layer.
>
> Raw telemetry streamed into bronze. Lakeflow enriched and scored it. The triage board showed the score moving as evidence arrived. We saw why exposure, timing, identity, and business context matter more than feed confidence alone.

## Act 3: Agentic Investigation And Human Approval

Target time: 25 minutes.

Goal: Show that the agent investigates with tools, writes a grounded brief, and routes high-impact actions to a human.

### Act 3 Opening

Show the hero finding crossing the agent threshold.

Say:

> Act 3 starts when the hero finding crosses the investigation threshold.
>
> This is where the agent begins. The agent is not guessing from a prompt alone. It is going to call tools against governed data.

### Explain Agentic Investigation

Say:

> An agentic investigation means the system can take multiple reasoning steps.
>
> It can ask for telemetry. It can check auth anomalies. It can fetch user context. It can look up campaign clustering. It can check policy. It can search prior case memory.
>
> The important control is that every tool call is recorded. We can inspect the trace afterward.

### Show Agent Started

Point to `agent.started` or the UI trace indicator.

Say:

> The agent has started for `tesco-clubcard-support[.]com`.
>
> You will see lightweight steps in the UI: querying telemetry, checking auth anomalies, getting user context, checking policy, and writing the brief.

### Tool 1: Query Telemetry

When the agent calls `query_telemetry(domain)`, say:

> First, the agent asks: what internal activity touched this domain?
>
> It retrieves DNS hits, proxy hits, email clicks, and sample events. This is the exposure question.
>
> For the hero domain, the answer is not tiny. Multiple employees clicked, and some posted data to the phishing path.

### Tool 2: Check Auth Anomalies

When the agent calls `check_auth_anomalies(employee_ids[])`, say:

> Next, the agent asks: did anything suspicious happen to those accounts afterward?
>
> This is important because a phishing click becomes more serious when followed by failed logins, lockouts, or a strange successful login.
>
> For Priya, the auth evidence is strong: a successful login from Romania, unknown device, after credential entry.

### Tool 3: Get User Context

When the agent calls `get_user_context(employee_ids[])`, say:

> Now the agent asks: who are these people?
>
> Security risk depends on business context. A compromised cloud admin is usually higher risk than a compromised low-privilege test account.
>
> Priya belongs to `Cloud-Admins`, so the recommended action becomes more serious.

### Tool 4: Get Campaign Cluster

When the agent calls `get_campaign_cluster(domain)`, say:

> Now the agent asks whether this domain belongs to a broader campaign.
>
> A campaign cluster uses shared infrastructure clues: hosting IPs, registrar, registrant email, kit fingerprint, and report co-mentions.
>
> Here, the domain maps to FreshCart PhishOps, with the `fc-kit-v3` phishing kit.

### Tool 5: Get Report Context

When the agent calls `get_report_context(domain)`, say:

> The agent also pulls report context.
>
> This gives it analyst-written background from the extracted reports: what the campaign is, which techniques it uses, and what detections are recommended.
>
> Because the reports were already turned into structured rows in Act 1, this is a governed lookup, not a random web search.

### Tool 6: Search Case Memory

When the agent calls `search_case_memory(finding_signature)`, say:

> The agent also checks case memory: have we adjudicated something like this before?
>
> Case memory holds prior confirmed, reason-coded decisions. If a similar case was already resolved, the agent should cite it by id instead of starting from scratch.
>
> For this hero finding there is no prior precedent yet, so the agent proceeds on the evidence. In Act 4 you will see this same memory make a later domain auto-close.

### Tool 7: Lookup Policy

When the agent calls `lookup_policy(domain, action)`, say:

> Finally, the agent checks policy.
>
> Policy decides what can auto-execute and what must go to a human. Confidence alone is not enough.
>
> In this system, tier-0 actions are low-impact. Tier-1 actions, like blocking a domain, may auto-execute only under strict conditions. Tier-2 actions, like password reset or account disable, never auto-execute.

### Explain The Human Gate

Say:

> This matters because the recommended action touches identity.
>
> Resetting a password or disabling an account can disrupt a real person and a real business process. Even if the model is confident, the action goes to the queue.
>
> This is not "AI does everything." This is "AI prepares the evidence and recommendation, then policy decides the control point."

### Show The Grounded Brief

Open the Approval Queue item.

Say:

> The agent has now written a brief.
>
> Notice the sections: what happened, who is affected, evidence, recommended action, and confidence.
>
> Also notice that the indicators are defanged. The brief should be safe to display and copy.

Read a summarized version:

> What happened: FreshCart PhishOps infrastructure sent a rewards-themed phishing email using `tesco-clubcard-support[.]com`.
>
> Who is affected: 17 employees clicked, 3 submitted credentials, including Priya Nair from Cloud Platform.
>
> Evidence: email click, proxy POST to `/wp-login-secure/`, failed-login burst, lockout, and Priya's successful login from Romania on an unknown device.
>
> Recommended action: queue a tier-2 identity action for Priya, such as password reset and session review, plus block or watchlist the domain.

### Explain Groundedness

Point to the groundedness judge score.

Say:

> Groundedness means the brief must be traceable to evidence.
>
> A grounded brief should not invent facts. If the brief says Priya had a Romania login, the trace should show where that came from.
>
> This judge is the live trust gate. Before anything auto-executes, the system checks that the agent's claims are grounded in tool output.

### Open MLflow Trace

Show the MLflow trace.

Say:

> This is the trace. It records the agent run: inputs, tool calls, outputs, timings, and scores.
>
> This matters for audit and debugging. If an analyst challenges the recommendation, we can inspect exactly how the agent reached it.
>
> In security, an unexplained answer is not enough. We need a record.

### Approve The Tier-2 Action

Back in Approval Queue, approve with an appropriate reason or notes.

Say:

> I am approving the queued action.
>
> The app records my human identity using on-behalf-of-user identity. That means the audit trail does not just say "the app did it." It says which human approved it.

Click Approve.

Say:

> The decision is now recorded. The queue updates. A feedback record is available for later evaluation and monitoring.

### Audience Genie Question

Open Genie or the trusted question UI.

Say:

> Now I will ask a natural-language hunting question over the same governed data.
>
> A safe rehearsed question is: which privileged users touched anything similar to a Tesco domain this week?

Run the question:

> Which privileged users touched anything similar to a Tesco domain this week?

Say after answer:

> Genie is not replacing the investigation flow. It is useful for ad-hoc hunting.
>
> The important part is that it is answering from trusted governed tables, not from memory or a random internet source.

### Act 3 Summary

Say:

> Act 3 showed the agent layer.
>
> The agent used tools, wrote a grounded brief, recorded an MLflow trace, and respected policy. The high-impact identity action went to a human queue, and the human approval was audited.

## Act 4: Close The Loop

Target time: 15 minutes.

Goal: Show that decisions become policy, memory, evaluation data, and detections.

### Act 4 Opening

Say:

> A SOC workflow is incomplete if every decision dies in a ticket.
>
> Act 4 is about closing the loop. The human decision becomes data. That data updates policy, creates memory, feeds evaluation, and can produce detection code.

### Learning Beat 1: Policy Exception

Inject `clubcard-summer-deals[.]com`.

Say:

> I am injecting a domain that looks suspicious: `clubcard-summer-deals[.]com`.
>
> It is recently registered, brand-like, and on consumer hosting. An automated system might think it is phishing.
>
> But in this synthetic world, it belongs to Tesco's own marketing agency. This is a false positive.

Show it entering the queue.

Say:

> The agent recommends escalation because the evidence looks suspicious.
>
> This is a good recommendation based on what it knows. But the human has extra business context: this is an approved vendor campaign.

Reject with reason code `policy_exception`.

Say:

> I am rejecting this as a policy exception.
>
> The reason code matters. If I mark it as wrong classification, the system learns that the agent classified the evidence incorrectly. If I mark it as policy exception, the system learns that the evidence was suspicious but policy says this specific domain is allowed.
>
> That distinction is important. We do not want to teach the agent that suspicious signals are safe. We want to teach the router that this vendor domain is allowed.

Show allowlist entry.

Say:

> The rejection creates a versioned allowlist entry in the policy store.
>
> Policy store is not just a settings file. It is governed operational data with versions, reasons, who added it, and which decision caused it.

### Learning Beat 2: Auto-Close From Memory Or Policy

Inject `clubcard-autumn-deals[.]com`.

Say:

> Now I inject a sibling domain: `clubcard-autumn-deals[.]com`.
>
> The point is to show immediate learning. The system can now recognize a related vendor-approved pattern and route it differently.

Show auto-close or policy citation.

Say:

> This time, the finding auto-closes or routes to a lower-impact path, citing the prior adjudication.
>
> That is the learning loop in miniature: human decision, reason code, policy update, changed future behavior.

### Explain Feedback Records

Show `feedback_records` or the UI summary.

Say:

> A feedback record is a structured record of the decision.
>
> It stores the decision id, verdict, reason code, notes, ground-truth label when available, and timestamp.
>
> This lets the system evaluate itself later. Which auto-resolutions were right? Which escalations were unnecessary? Which agent recommendations disagreed with humans?

### Explain Case Memory

Say:

> Case memory is a searchable memory of prior adjudicated cases.
>
> It should not contain every messy opinion. Only confirmed, reason-coded decisions enter memory.
>
> This is important because humans can be wrong too. The demo keeps ambiguous feedback out of memory and uses it for evaluation instead.

### Batch Improvement Reveal

Show the pre-baked v1-vs-v2 MLflow comparison.

Say:

> The live learning beat shows immediate behavior change. The batch improvement beat shows a slower improvement loop.
>
> Feedback records and traces become a versioned evaluation dataset in MLflow.
>
> The next agent version is compared against the current one before promotion. We look at agreement rate, escalation rate, groundedness, and precision on auto-close decisions.
>
> This is the software-engineering discipline we want for agents: traces, evals, versioning, shadow mode, and promotion only after measurement.

Status honesty note:

> The Agent Bricks optimization flow is a newer platform capability. In this demo, the comparison is pre-baked and clearly labeled if the live optimization API is not stable enough for demo day.

### Detection Export

Open the detection export view or Git folder.

Say:

> Now the investigation becomes detection code.
>
> From the FreshCart finding, the system generates Sigma rules. One rule looks for proxy traffic to the FreshCart kit path `/wp-login-secure/`. Another looks for DNS queries to top campaign domains.
>
> Sigma is useful because it is vendor-neutral. The same detection idea can be converted into the query language of a target tool.

Show validation and backtest metrics.

Say:

> The rule is not accepted just because an agent wrote it.
>
> It is serialized, validated through pySigma, converted to a target query, and backtested against 30 days of historical bronze telemetry.
>
> The backtest checks hits, false-positive rate, and recall against known ground truth. Only a passing rule is proposed.

Facilitator color, optional to say aloud:

> Detections-as-code is the direction here. Databricks acquired the creator of SPL, the Splunk search language, through SiftD.ai. So generating a rule, validating it, backtesting it, and versioning it in Git is a natural fit.

Show Git output.

Say:

> The rule is written to Git. This matters because detection engineering should be reviewable, versioned, and deployable like code.

### Campaign Graph

Show the campaign graph.

Say:

> Finally, we look at the campaign graph.
>
> The graph connects indicators that share infrastructure: hosting IP, registrant email, kit id, or report co-mentions.
>
> The headline is: 455 indicators become 3 campaigns plus noise.
>
> This helps analysts move from individual indicators to attacker infrastructure. Instead of blocking one domain at a time, the SOC can understand the campaign shape.

Point to the hero node.

Say:

> The starred node is the hero domain, `tesco-clubcard-support[.]com`.
>
> The surrounding nodes show related FreshCart infrastructure. This is how threat intelligence becomes campaign-level understanding.

### Act 4 Summary

Say:

> Act 4 closed the loop.
>
> A human decision updated policy. A related domain changed route. Feedback became an evaluation dataset. The investigation became Sigma detection code. The campaign graph turned many indicators into a smaller number of attacker clusters.
>
> This is the difference between a one-off alert and a learning SOC workflow.

## Closing Script

Show the runtime flow diagram again.

Say:

> Let us return to the architecture now that we have seen the story.
>
> The Director Console replayed events. Lakeflow enriched and scored them. The triage agent investigated the high-risk finding. The policy router separated low-impact automation from human-gated identity actions. The human decision flowed back into feedback, memory, evaluation, and detections.
>
> The main idea is not that AI magically solves SOC work. The main idea is that governed data, deterministic evidence, agentic investigation, and human feedback can live in one loop.

### Production Path

Say:

> To move this from demo to production, the synthetic feeds would become real feed connectors. The replayed telemetry would become live enterprise telemetry. The static enrichment tables would become real enrichment providers. The policy store would be owned by the SOC. The evaluation dataset would grow from real analyst decisions.
>
> The same architecture still applies: evidence first, agent second, policy gate third, feedback always.

### Status Honesty

Say:

> Most of what you saw is built from generally available Databricks primitives: Unity Catalog, Delta, Lakeflow, Lakebase, Databricks Apps, FMAPI, AI Gateway, Agent Bricks, Document Intelligence, and MLflow 3.
>
> The optional external access pattern uses Context-Based Ingress, which is public preview. Managed Omnigent is shown only as a forward-looking enforcement direction. Lakewatch is mentioned only as the productized SIEM direction, not as the core demo dependency.

### Final Line

Say:

> The takeaway is simple: the best SOC automation is not blind automation. It is governed evidence, explainable investigation, measured action, and learning from every decision.

## Fallback Script

Use this section if something breaks during the demo.

### Replay Stalls

Action: click `Skip-to-T-1`.

Say:

> I am going to jump the simulation clock forward. The replay is deterministic, so this takes us to the same evidence state without waiting for the stream.

### Agent Endpoint Hiccups

Action: click `Load-precomputed-brief`.

Say:

> The live agent endpoint is not responding quickly enough for a room demo, so I am loading the precomputed brief for the same finding.
>
> The evidence and trace shape are the same. This fallback keeps the narrative moving without changing the investigation result.

### Auto-Trigger Misfires

Action: click `Fire-agent-manually`.

Say:

> The automatic trigger did not fire, so I am manually starting the agent for this finding. In production, this trigger would be monitored like any other workflow dependency.

### Genie Question Is Risky

Action: use the trusted question:

> Which privileged users touched anything similar to a Tesco domain this week?

Say:

> I will use a rehearsed trusted question so we stay focused on the demo path.

### Live Model Call Fails

Action: keep the board running from synced state.

Say:

> The live model call failed, but the deterministic pipeline and operational state are still running. This is why the demo separates evidence, policy, and model reasoning.

### Detection Export Fails

Action: show pre-generated Sigma files.

Say:

> The live export path is not completing in time, so I am showing the generated rule artifacts. The important pattern is still visible: finding to Sigma, validation, backtest, Git.

## Presenter Cheat Sheet By Act

### Opening

Key phrase:

> Outside intelligence plus inside exposure equals SOC priority.

Do not forget:

- The data is synthetic.
- The workflow is real.
- Evidence comes before AI.

### Act 1

Key phrase:

> Use both: regex for cheap deterministic extraction, AI for language understanding.

Do not forget:

- Define structured feeds.
- Define reports.
- Explain bronze, silver, gold.
- Show `tesco-parcel-tracking[.]net` as the feed-gap payoff.

### Act 2

Key phrase:

> The score climbs because evidence accumulates.

Do not forget:

- Explain each risk component.
- Call out counterexamples.
- Make Priya's privileged context clear.
- Say that high confidence alone is not enough.
- Point at the Metrics Strip counters and gateway token and cost.

### Act 3

Key phrase:

> The agent investigates with tools, and the trace proves what it did.

Do not forget:

- Show tool calls.
- Show grounded brief.
- Show groundedness score.
- Show MLflow trace.
- Approve the tier-2 action with human identity.

### Act 4

Key phrase:

> Every decision becomes future training and policy data.

Do not forget:

- Use `policy_exception`, not a generic rejection.
- Show the allowlist or policy update.
- Inject the sibling domain.
- Show Sigma export and graph if time allows.

## Common Audience Questions

### Is AI deciding to disable accounts?

Answer:

> No. Identity-impacting actions are tier-2 actions, and the policy router always sends them to a human queue. The agent can recommend, but it cannot auto-disable an account in this demo.

### Why not just block every suspicious domain?

Answer:

> Blocking everything creates false positives and business disruption. Some domains look suspicious but are legitimate, like the marketing-agency example. The system uses evidence, policy, and human feedback to avoid blunt automation.

### Why use Databricks for SOC data?

Answer:

> SOC work needs large-scale data joins, streaming updates, governance, AI, traces, apps, and feedback loops. The lakehouse lets those live in one governed architecture instead of scattered systems.

### What is the difference between an alert and this finding?

Answer:

> An alert is a raw signal. This finding is a correlated evidence package. It includes threat intel, internal exposure, identity context, scoring components, and a recommended route.

### Why use AI if the score is deterministic?

Answer:

> The deterministic score prioritizes and explains the core evidence. AI helps with language-heavy tasks: extracting reports, summarizing evidence, comparing context, and writing a human-readable brief. The model is not the only source of truth.

### What prevents hallucination?

Answer:

> The brief is constrained to tool output, indicators are defanged, the full trace is recorded, and a groundedness judge checks whether claims are supported by evidence. High-impact actions still require human approval.

### What happens after the demo?

Answer:

> In production, the replay becomes live telemetry, synthetic feeds become real feed connectors, policy is owned by the SOC, and feedback records become the evaluation set for future agent versions.

## Final Checklist Before Presenting

- Run `00_load_world`.
- Run `99_validate`.
- Confirm `pytest datagen/tests` is green if developing locally.
- Confirm Lakebase schema applies and policy store is seeded.
- Confirm replay starts from the Director Console.
- Confirm `tesco-clubcard-support[.]com` reaches rank 1.
- Confirm the agent writes a brief for the hero finding.
- Confirm the tier-2 action enters the Approval Queue.
- Confirm Approve and Reject write feedback records.
- Confirm `clubcard-summer-deals[.]com` creates the policy-exception beat.
- Confirm `clubcard-autumn-deals[.]com` routes differently after the exception.
- Confirm MLflow trace renders.
- Confirm Sigma export assets are available.
- Confirm campaign graph image is available.
- Confirm every displayed indicator is defanged.
- Confirm no presenter-facing text uses preview features without a caveat.




