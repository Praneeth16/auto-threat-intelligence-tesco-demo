"""Triage agent runner (PLAN 8.1).

Runs the full tool loop on one finding, assembles grounded evidence, asks the
FMAPI model to write the brief under the Section 8.1 constraints, recommends an
action with a tier and confidence, and returns a queue-ready record.

Single agent, not a multi-agent supervisor: debuggable on demo morning. The
tool loop is a deterministic sequence (query telemetry, check auth, get user
context, get campaign cluster, get report context, search case memory) so the
Triage Board can show lightweight step markers live and MLflow captures the
trace. Every model call egresses through the FMAPI serving endpoint (AI Gateway).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from agents.tools.check_auth_anomalies import check_auth_anomalies
from agents.tools.get_campaign_cluster import get_campaign_cluster
from agents.tools.get_report_context import get_report_context
from agents.tools.get_user_context import get_user_context
from agents.tools.query_telemetry import query_telemetry
from agents.tools.search_case_memory import finding_signature, search_case_memory
from agents.triage_agent.prompt import SYSTEM_PROMPT
from datagen.common import defang


@dataclass
class Evidence:
    """Everything the tools returned, the only facts the brief may use."""

    domain: str
    telemetry: dict
    auth: dict
    user_context: dict
    campaign: dict
    report_context: dict
    case_memory: dict
    tool_sequence: list[str] = field(default_factory=list)


@dataclass
class TriageResult:
    finding_id: str
    domain: str
    brief: str
    recommended_action: str
    action_tier: int
    agent_confidence: float
    evidence: Evidence
    tool_sequence: list[str]


# Tool loop order (shown as live step markers on the Triage Board).
TOOL_SEQUENCE = [
    "query_telemetry", "check_auth_anomalies", "get_user_context",
    "get_campaign_cluster", "get_report_context", "search_case_memory",
]


def gather_evidence(domain: str, world) -> Evidence:
    """Run the deterministic tool loop against the loaded world/frames."""
    dns, proxy, email, auth = (world.telemetry.dns, world.telemetry.proxy,
                               world.telemetry.email, world.telemetry.auth)
    telem = query_telemetry(domain, dns, proxy, email)
    affected = telem["sample_users"]
    auth_res = check_auth_anomalies(affected, auth, world.employees)
    user_ctx = get_user_context(affected, world.employees)
    campaign = get_campaign_cluster(domain, world.iocs, world.ioc_enrichment, world.gt_campaigns)
    report_ctx = get_report_context(domain, world.gt_report_entities)
    sig = finding_signature(domain, campaign.get("campaign_id"), "block-domain-at-proxy")
    case_mem = search_case_memory(sig, pool=None)  # pool wired in-app
    return Evidence(domain, telem, auth_res, user_ctx, campaign, report_ctx,
                    case_mem, tool_sequence=list(TOOL_SEQUENCE))


def recommend_action(ev: Evidence) -> tuple[str, int, float]:
    """Deterministic recommendation from evidence (the tier the router enforces).

    Credential entry by a privileged user -> tier-2 password-reset (the AP1
    beat). Credential entry without privilege or a strong block signal ->
    tier-1 block. Otherwise add-to-watchlist or close.
    """
    priv = ev.user_context.get("any_privileged", False)
    cred = ev.telemetry.get("credential_posts", 0) > 0
    foreign = any(u["foreign_success"] > 0 for u in ev.auth.get("employees", []))
    users = ev.telemetry.get("distinct_users", 0)

    if cred and priv:
        # Privileged credential compromise: reset the account (tier 2, human).
        return "password-reset", 2, 0.9
    if cred or foreign:
        return "block-domain-at-proxy", 1, 0.8
    if users >= 2:
        return "add-to-watchlist", 0, 0.7
    return "close-as-benign", 0, 0.5


def _evidence_facts(ev: Evidence) -> str:
    """Serialize the tool output as the grounding the model may use."""
    lines = [
        f"domain: {defang(ev.domain)}",
        f"telemetry: {ev.telemetry}",
        f"auth: {ev.auth}",
        f"user_context: {ev.user_context}",
        f"campaign: {ev.campaign}",
        f"report_context: {ev.report_context}",
        f"case_memory: {ev.case_memory}",
    ]
    return "\n".join(lines)


def write_brief(ev: Evidence, action: str, tier: int, confidence: float,
                endpoint: str | None = None, client=None) -> str:
    """Ask the FMAPI model to write the grounded brief, or build it locally.

    When no serving client is available (offline reference build), a
    deterministic template brief is produced from the same evidence so the
    demo path is rehearsable without a live model.
    """
    facts = _evidence_facts(ev)
    if client is not None:
        from agents.tools import _serving  # lazy; see note below

        return _serving.chat_brief(endpoint, SYSTEM_PROMPT, facts, action, tier, confidence, client)
    return _template_brief(ev, action, tier, confidence)


def _template_brief(ev: Evidence, action: str, tier: int, confidence: float) -> str:
    """Deterministic grounded brief from evidence (offline / fallback)."""
    d = defang(ev.domain)
    t = ev.telemetry
    priv_names = [u["full_name"] for u in ev.user_context.get("users", []) if u["is_privileged"]]
    who = ", ".join(priv_names) if priv_names else f"{t.get('distinct_users', 0)} employees"
    camp = ev.campaign.get("campaign_name") or "an unclustered domain"
    reports = ev.report_context.get("reports", [])
    case_line = ""
    if ev.case_memory.get("matches"):
        case_line = f" Prior case {ev.case_memory['matches'][0]['case_id']} applies."
    return (
        f"What happened: The domain {d} is part of {camp} and drew internal "
        f"contact.\n"
        f"Who is affected: {who}.\n"
        f"Evidence: {t.get('distinct_users', 0)} distinct users, "
        f"{t.get('credential_posts', 0)} credential submissions, "
        f"{t.get('dns_hits', 0)} DNS and {t.get('proxy_hits', 0)} proxy hits. "
        f"Reports: {', '.join(reports) if reports else 'none'}.{case_line}\n"
        f"Recommended action: {action} (tier {tier}).\n"
        f"Confidence: {confidence:.0%}."
    )


def run_triage(finding_id: str, domain: str, world, endpoint=None, client=None) -> TriageResult:
    """Full triage: tool loop -> recommendation -> grounded brief."""
    ev = gather_evidence(domain, world)
    action, tier, confidence = recommend_action(ev)
    brief = write_brief(ev, action, tier, confidence, endpoint=endpoint, client=client)
    return TriageResult(finding_id, domain, brief, action, tier, confidence, ev, ev.tool_sequence)
