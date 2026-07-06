"""Stage 9 gates (PLAN 11, 13.1): Sigma rules validate through pySigma and
convert to SPL; the campaign graph yields 3 labeled communities.
"""

from __future__ import annotations

import pandas as pd
import pytest

from datagen.ground_truth import build_world
from pipelines.detections.sigma_export import (
    build_hero_rules, dns_campaign_domains_rule, proxy_kit_path_rule,
    to_splunk, to_yaml, validate_sigma,
)
from pipelines.graph.campaign_graph import build_campaign_graph

ANCHOR = pd.Timestamp("2026-07-06 00:00:00")


@pytest.fixture(scope="module")
def world():
    return build_world(anchor=ANCHOR)


# ---- Sigma export (PLAN 11.1) ----------------------------------------------
def test_hero_rules_validate_through_pysigma():
    for rule in build_hero_rules():
        assert validate_sigma(to_yaml(rule))


def test_proxy_rule_converts_to_spl_with_kit_path():
    spl = to_splunk(to_yaml(proxy_kit_path_rule("/wp-login-secure/")))
    assert "wp-login-secure" in spl


def test_dns_rule_converts_to_spl_with_domains():
    spl = to_splunk(to_yaml(dns_campaign_domains_rule(["tesco-clubcard-support.com"])))
    assert "tesco-clubcard-support.com" in spl


def test_rule_ids_are_deterministic():
    a = proxy_kit_path_rule("/wp-login-secure/")["id"]
    b = proxy_kit_path_rule("/wp-login-secure/")["id"]
    assert a == b  # uuid5, reproducible


# ---- Campaign graph (PLAN 11.3) --------------------------------------------
def test_graph_yields_three_communities(world):
    result = build_campaign_graph(world.iocs, world.ioc_enrichment, world.gt_campaigns)
    assert len(result.communities) == 3


def test_communities_labeled_by_majority_campaign(world):
    result = build_campaign_graph(world.iocs, world.ioc_enrichment, world.gt_campaigns)
    labels = {c["campaign"] for c in result.labeled}
    assert labels == {"A", "B", "C"}
    names = {c["campaign_name"] for c in result.labeled}
    assert "FreshCart PhishOps" in names


def test_every_community_has_at_least_ten_nodes(world):
    result = build_campaign_graph(world.iocs, world.ioc_enrichment, world.gt_campaigns)
    assert all(len(c) >= 10 for c in result.communities)


# ---- Backtesting (PLAN 11.1, 11.2) -----------------------------------------
def test_proxy_rule_backtest_recalls_hero(world):
    from pipelines.detections.backtest import backtest_proxy_rule
    from datagen import config

    bt = backtest_proxy_rule(world.telemetry.proxy, "/wp-login-secure/",
                             true_positive_domains={config.HERO_DOMAIN})
    assert bt.hits > 0
    assert bt.recall >= 0.5
    assert bt.passes


def test_threshold_backtest_measures_tradeoff(world):
    from pipelines.detections.backtest import backtest_threshold

    bt = backtest_threshold(world.filler_pool, threshold=0.85)
    # Auto-lanes clear real analyst hours; escalations are the ambiguous items.
    assert bt.analyst_hours_cleared > 0
    assert bt.escalations > 0
    # needs_review items must NOT land in an auto-close lane (the filler pool is
    # pre-validated), so wrong auto-closes are zero.
    assert bt.wrong_auto_closes == 0
