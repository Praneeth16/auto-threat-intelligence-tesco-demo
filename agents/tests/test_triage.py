"""Triage agent gate (PLAN 13.1): the agent runs its full tool loop on the hero
finding, writes a grounded brief, and the router queues the tier-2 action.
"""

from __future__ import annotations

import pandas as pd
import pytest

from agents.router.policy_router import route
from agents.tools.query_telemetry import query_telemetry
from agents.triage_agent.run import gather_evidence, recommend_action, run_triage
from agents.triage_agent.prompt import brief_sections
from datagen import config
from datagen.common import defang
from datagen.ground_truth import build_world

ANCHOR = pd.Timestamp("2026-07-06 00:00:00")


@pytest.fixture(scope="module")
def world():
    return build_world(anchor=ANCHOR)


def test_tool_loop_runs_all_tools(world):
    ev = gather_evidence(config.HERO_DOMAIN, world)
    assert ev.tool_sequence == [
        "query_telemetry", "check_auth_anomalies", "get_user_context",
        "get_campaign_cluster", "get_report_context", "search_case_memory",
    ]


def test_hero_evidence_is_grounded(world):
    ev = gather_evidence(config.HERO_DOMAIN, world)
    # 17 clickers, 3 credential posts, Priya privileged, FreshCart campaign.
    assert ev.telemetry["distinct_users"] == config.AP1_CLICKERS
    assert ev.telemetry["credential_posts"] == config.AP1_CREDENTIAL_SUBMITTERS
    assert ev.user_context["any_privileged"]
    assert ev.campaign["campaign_name"] == "FreshCart PhishOps"


def test_hero_recommends_tier2_password_reset(world):
    ev = gather_evidence(config.HERO_DOMAIN, world)
    action, tier, conf = recommend_action(ev)
    # Privileged credential compromise -> tier-2 password reset.
    assert action == "password-reset"
    assert tier == 2


def test_hero_action_routes_to_human_queue(world):
    result = run_triage("F-hero", config.HERO_DOMAIN, world)
    d = route(result.recommended_action, domain=config.HERO_DOMAIN,
              exact_ioc_match=True, risk_score=82, brand_similarity=90,
              model_confidence=result.agent_confidence, groundedness_passed=True)
    # Tier-2 identity action always queued for human approval.
    assert d.route == "human_queue"
    assert d.action_tier == 2


def test_brief_has_all_sections_and_is_defanged(world):
    result = run_triage("F-hero", config.HERO_DOMAIN, world)
    for section in brief_sections():
        assert section in result.brief, f"missing section: {section}"
    # Hero domain appears only defanged in the brief.
    assert config.HERO_DOMAIN not in result.brief
    assert defang(config.HERO_DOMAIN) in result.brief


def test_brief_introduces_no_absent_facts(world):
    """The brief's user count matches the tool output, not an invented number."""
    result = run_triage("F-hero", config.HERO_DOMAIN, world)
    telem = query_telemetry(config.HERO_DOMAIN, world.telemetry.dns,
                            world.telemetry.proxy, world.telemetry.email)
    assert str(telem["distinct_users"]) in result.brief


def test_feed_gap_domain_surfaces_via_report_context(world):
    """AP3: the report-only domain has report context but no campaign feed."""
    ev = gather_evidence(config.REPORT_ONLY_DOMAIN, world)
    assert ev.report_context["report_only"]
    assert "R14" in ev.report_context["reports"]
