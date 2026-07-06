"""Policy router gates (PLAN 8.4, 13.1).

Tier-2 identity actions never auto-execute at any confidence. Tier-1 block
auto-executes only on an exact high-confidence IOC match. Tier-0 auto-executes
above threshold. Allowlist precedes tiering (the autumn-sibling auto-close).
"""

from __future__ import annotations

from agents.router.policy_router import composite_confidence, route


def test_tier2_never_auto_even_at_max_confidence():
    d = route("password-reset", domain="tesco-clubcard-support.com",
              exact_ioc_match=True, risk_score=100, brand_similarity=100,
              model_confidence=1.0, groundedness_passed=True)
    assert d.route == "human_queue"
    assert d.action_tier == 2
    assert not d.reversible


def test_account_disable_also_tier2_human():
    d = route("account-disable", domain="x.com", exact_ioc_match=True,
              risk_score=99, brand_similarity=99, model_confidence=1.0,
              groundedness_passed=True)
    assert d.route == "human_queue" and d.action_tier == 2


def test_tier1_block_auto_only_on_exact_ioc():
    auto = route("block-domain-at-proxy", domain="x.com", exact_ioc_match=True,
                 risk_score=90, brand_similarity=90, model_confidence=0.8,
                 groundedness_passed=True)
    assert auto.route == "auto_execute" and auto.action_tier == 1 and auto.reversible

    queued = route("block-domain-at-proxy", domain="x.com", exact_ioc_match=False,
                   risk_score=90, brand_similarity=90, model_confidence=0.8,
                   groundedness_passed=True)
    assert queued.route == "human_queue"


def test_tier1_block_queued_if_groundedness_fails():
    d = route("block-domain-at-proxy", domain="x.com", exact_ioc_match=True,
              risk_score=90, brand_similarity=90, model_confidence=0.9,
              groundedness_passed=False)
    assert d.route == "human_queue"


def test_tier0_auto_above_threshold():
    d = route("add-to-watchlist", domain="x.com", exact_ioc_match=True,
              risk_score=90, brand_similarity=90, model_confidence=0.9,
              groundedness_passed=True)
    assert d.route == "auto_execute" and d.action_tier == 0
    assert d.composite_confidence >= 0.85


def test_tier0_queued_below_threshold():
    d = route("close-as-benign", domain="x.com", exact_ioc_match=False,
              risk_score=20, brand_similarity=20, model_confidence=0.2,
              groundedness_passed=True)
    assert d.route == "human_queue"


def test_allowlist_auto_closes_before_tiering():
    """The autumn sibling auto-closes citing the recorded summer exception."""
    d = route("block-domain-at-proxy", domain="clubcard-autumn-deals.com",
              exact_ioc_match=True, risk_score=90, brand_similarity=90,
              model_confidence=0.9, groundedness_passed=True,
              allowlist={"clubcard-autumn-deals.com"})
    assert d.route == "auto_execute"
    assert d.action == "close-as-benign"
    assert d.allowlisted


def test_composite_confidence_deterministic_dominant():
    """Deterministic signals dominate; model self-report is a minor input."""
    high_det = composite_confidence(True, 90, 90, 0.0)   # no model input
    low_det_high_model = composite_confidence(False, 10, 10, 1.0)  # only model
    assert high_det > low_det_high_model
