"""Tests for the seeded policy tier matrix (PLAN 8.4). No live DB required."""

from __future__ import annotations

from app.db.seed_policy_store import POLICY_V1, PolicyRow


def _by_action(action: str) -> PolicyRow:
    return next(p for p in POLICY_V1 if p.action == action)


def test_tier0_actions_auto_with_threshold():
    for action in ("close-as-benign", "merge-duplicate", "add-to-watchlist", "enrich"):
        p = _by_action(action)
        assert p.tier == 0
        assert p.auto_threshold == 0.85
        assert not p.requires_exact_ioc


def test_tier1_block_requires_exact_ioc_and_reversible():
    p = _by_action("block-domain-at-proxy")
    assert p.tier == 1
    assert p.requires_exact_ioc  # auto only on exact high-confidence IOC match
    assert p.notify
    assert p.reversible
    assert p.auto_threshold is None  # not a plain threshold gate


def test_tier2_identity_actions_never_auto():
    for action in ("password-reset", "account-disable"):
        p = _by_action(action)
        assert p.tier == 2
        assert p.auto_threshold is None  # never auto, any confidence
        assert not p.reversible  # identity actions are not reversible


def test_all_actions_have_valid_tier():
    assert {p.tier for p in POLICY_V1} == {0, 1, 2}
    assert len(POLICY_V1) == 7
