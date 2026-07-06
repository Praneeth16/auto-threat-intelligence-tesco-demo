# Demo runbook: FreshCart PhishOps

Four acts on the autonomy ladder: manual hunt, AI-assisted enrichment, agentic
investigation with human approval, agent-authored detections backtested before
review. Total ~80 minutes. Never cut Act 2's climbing score or Act 3's agent
trace and approval.

## Pre-flight checklist

Run before every rehearsal and on demo morning:

- [ ] `pytest` green locally.
- [ ] `pipelines/00_load_world.py` then `pipelines/99_validate.py` pass in-workspace with zero manual edits.
- [ ] Lakebase schema applied; `policy_store` seeded; synced tables readable.
- [ ] Dry-run the full replay end to end.
- [ ] Confirm the agent endpoint responds and the trace renders.
- [ ] Assemble and screenshot the metrics dashboard.
- [ ] Verify the Git folder and the scheduled detection Job.
- [ ] Rehearse the audience Genie question.
- [ ] Confirm OBO identity stamping on an approve.

## Act 1: The advisory drops (~20 min)

Open on the classical foundation the room knows. Show STIX, MISP, and CSV feeds
parsed into one governed `silver_iocs` table, with typosquat distance and
registrar/ASN features attached. Then the blend beat: run the regex-vs-agent
extraction diff on the FreshCart reports. Regex catches the clean indicators;
the agent additionally catches the defanged and prose-described ones plus TTPs.
State the takeaway: use both, regex as the cheap deterministic pass, AI for what
it cannot reach.

Then drop report R14 into the Volume live. Extraction turns it into rows; the
anti-join reveals `tesco-parcel-tracking[.]net` is in no feed; a hunt join finds
2 internal DNS hits from 4 days ago. Introduce bronze/silver/gold, Unity
Catalog, and FMAPI while doing the work.

Payoff: classical and AI on the same task, then intel to internal exposure in a
few statements.

## Act 2: The attack replays live (~20 min, centerpiece)

Click Run on the Director Console. 72 simulated hours stream into bronze in
about 6 minutes. Lakeflow enriches and scores continuously. On the Live Triage
Board the hero domain `tesco-clubcard-support[.]com` climbs from roughly 40 to
the low 80s as each signal lands, and Priya Nair's compromise assembles on
screen. This is the one-platform argument made visceral. Do not cut this.

## Act 3: Agentic investigation and audience question (~25 min)

The hero finding crosses threshold; the triage agent fires automatically. Its
tool loop renders live (querying telemetry, checking auth anomalies, reading
user context, clustering the campaign, pulling report context, searching case
memory). It writes a grounded brief and queues a tier-2 password reset for
Priya, which the presenter approves with OBO identity stamped.

Then take a question from the room into the curated Genie space, for example
"which privileged users touched anything similar to a Tesco domain this week?",
answered live. Close on the judge score: why the brief is trustworthy.

## Act 4: Close the loop (~15 min)

The learning beats:

1. Inject `clubcard-summer-deals[.]com`. The agent escalates recommending a
   block. The presenter rejects with `policy_exception` (known vendor). A
   versioned allowlist entry lands in `policy_store`. The presenter injects
   `clubcard-autumn-deals[.]com`; it auto-closes citing the adjudicated case.
2. The pre-baked v1-vs-v2 MLflow improvement reveal, with the metrics strip
   showing agreement rate trending up. This comparison is labeled ILLUSTRATIVE;
   caveat it as such.

Then Sigma export to Git to a scheduled detection Job firing against replay
data, and the campaign graph (455 indicators to 3 campaigns). End on the
architecture diagram the room now understands and the production path. One
honest closing mention of Lakewatch as the productized direction; the demo ran
on GA primitives.

## Fallbacks (Director Console buttons + pre-baked assets)

- Replay stalls: Skip-to-T-1 (a two-second jump).
- Agent endpoint hiccups: Load-precomputed-brief for the hero.
- Auto-trigger misfires: Fire-agent-manually.
- Genie question risky: fall back to a rehearsed trusted question.
- Any live model call fails: the metrics strip and boards keep running on synced
  state.

Cut order if behind: the audience Genie question becomes a rehearsed one; the
graph shrinks to 2 minutes; the dashboard becomes a screenshot. Never cut Act 2's
climbing score or Act 3's agent trace and approval.
