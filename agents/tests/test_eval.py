"""Feedback taxonomy, judges, and the Act 4 learning beat (PLAN 10).

The key integration: a policy_exception reject writes an allowlist entry (not
case memory), and the router then auto-closes the sibling domain citing the
allowlist. This is the demo's close-the-loop moment.
"""

from __future__ import annotations

import pandas as pd
import pytest

from agents.eval.feedback_processor import process_feedback
from agents.eval.judges import GROUNDEDNESS_GATE, action_appropriateness, groundedness
from agents.eval.reason_codes import Destination, route_feedback
from agents.router.policy_router import route
from agents.triage_agent.run import gather_evidence, run_triage
from datagen import config
from datagen.ground_truth import build_world

ANCHOR = pd.Timestamp("2026-07-06 00:00:00")


@pytest.fixture(scope="module")
def world():
    return build_world(anchor=ANCHOR)


# ---- reason-code routing (PLAN 10.1) ---------------------------------------
def test_policy_exception_does_not_enter_case_memory():
    r = route_feedback("policy_exception")
    assert not r.enters_case_memory
    assert Destination.ALLOWLIST in r.destinations
    assert Destination.POLICY_STORE in r.destinations
    assert Destination.CASE_MEMORY not in r.destinations


def test_wrong_classification_enters_case_memory():
    r = route_feedback("wrong_classification")
    assert r.enters_case_memory
    assert Destination.EVAL_DATASET in r.destinations


def test_wrong_action_routes_to_policy_review():
    r = route_feedback("wrong_action")
    assert Destination.POLICY_REVIEW in r.destinations


def test_unknown_reason_code_raises():
    with pytest.raises(ValueError):
        route_feedback("made_up_code")


# ---- judges (PLAN 10.2) ----------------------------------------------------
def test_groundedness_passes_for_grounded_brief(world):
    result = run_triage("F-hero", config.HERO_DOMAIN, world)
    ev = {"telemetry": result.evidence.telemetry, "campaign": result.evidence.campaign}
    j = groundedness(result.brief, ev)
    assert j.passed
    assert j.score >= GROUNDEDNESS_GATE


def test_groundedness_fails_for_invented_number(world):
    ev = gather_evidence(config.HERO_DOMAIN, world)
    evd = {"telemetry": ev.telemetry, "campaign": ev.campaign}
    # A brief asserting an unsupported large count fails.
    bad = "Evidence: 9999 distinct users touched the domain."
    j = groundedness(bad, evd)
    assert not j.passed


def test_action_appropriateness_privileged_credential_is_tier2(world):
    ev = gather_evidence(config.HERO_DOMAIN, world)
    evd = {"user_context": ev.user_context, "telemetry": ev.telemetry}
    # Recommending tier 2 for the privileged credential compromise is appropriate.
    assert action_appropriateness(2, evd).passed
    # Under-tiering (tier 0) is not.
    assert not action_appropriateness(0, evd).passed


# ---- Act 4 close-the-loop beat (PLAN 10.5) ---------------------------------
def test_policy_exception_summer_then_autumn_auto_closes():
    """The full learning beat without a live DB, using an in-memory allowlist."""
    # 1. Presenter rejects clubcard-summer with policy_exception.
    summary = process_feedback(
        reason_code="policy_exception",
        domain="clubcard-summer-deals.com",
        campaign_id="A",
        recommended_action="block-domain-at-proxy",
        verdict="disagree",
        brief_excerpt="Known vendor marketing domain.",
        decision_id=1, identity="analyst@tesco-demo.example", policy_version=1,
        pool=None,
    )
    assert "allowlist" not in summary["written"]  # no pool -> dry run
    assert summary["enters_case_memory"] is False

    # Simulate the allowlist now containing both the summer domain and, per the
    # plan, its recorded family so the sibling is covered.
    allowlist = {"clubcard-summer-deals.com", "clubcard-autumn-deals.com"}

    # 2. Presenter injects clubcard-autumn; the router auto-closes it.
    decision = route(
        "block-domain-at-proxy", domain="clubcard-autumn-deals.com",
        exact_ioc_match=True, risk_score=80, brand_similarity=90,
        model_confidence=0.85, groundedness_passed=True, allowlist=allowlist,
    )
    assert decision.route == "auto_execute"
    assert decision.action == "close-as-benign"
    assert decision.allowlisted
