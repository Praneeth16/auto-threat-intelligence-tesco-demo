"""Stage 4 gates: scoring, extraction diff, similarity, feed dedup.

The demo-critical asserts (PLAN 13.1) proven against the datagen world with a
fixed anchor. If the hero does not rank #1 here, the demo is unsafe.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from datagen import config
from datagen.feeds import write_csv_feed, write_misp_events, write_stix_bundle
from datagen.ground_truth import build_world
from pipelines.classical.feed_parse import build_silver_iocs
from pipelines.classical.ioc_regex import build_silver_iocs_regex
from pipelines.classical.typosquat import brand_similarity
from pipelines.stream.candidates import build_candidates
from pipelines.stream.extraction_diff import build_extraction_diff, has_ai_only_recovery
from pipelines.stream.scoring import compute_findings, report_only_metric

ANCHOR = pd.Timestamp("2026-07-06 00:00:00")


@pytest.fixture(scope="module")
def world():
    return build_world(anchor=ANCHOR)


@pytest.fixture(scope="module")
def gold(world):
    cands = build_candidates(world.reference_ts)
    return compute_findings(cands, world.telemetry.dns, world.telemetry.proxy,
                            world.employees, world.reference_ts)


# ---------------------------------------------------------------------------
# Scoring: hero rank #1 and component firing (PLAN 5.4, 13.1)
# ---------------------------------------------------------------------------
def test_hero_ranks_first(gold):
    assert gold.iloc[0]["domain"] == config.HERO_DOMAIN


def test_hero_components_fire_except_repeat(gold):
    hero = gold[gold["domain"] == config.HERO_DOMAIN].iloc[0]
    assert hero["distinct_users_hit"] == config.AP1_CLICKERS  # 17
    assert hero["credential_entry_flag"] == 1
    assert hero["privileged_user_flag"] == 1  # Priya
    assert hero["repeat_access_flag"] == 0  # all except repeat-access
    assert hero["brand_similarity_score"] >= 85


def test_top_five_are_the_attack_paths(gold):
    top5 = set(gold.head(5)["domain"])
    expected = {
        config.HERO_DOMAIN, "tesco-supplier-billing.com",
        "tescobank-secure-auth.com", config.REPORT_ONLY_DOMAIN,
        "tesco-rewards-login.com",
    }
    assert top5 == expected


def test_counterexamples_below_all_attack_paths(gold):
    ap_domains = {
        config.HERO_DOMAIN, "tesco-supplier-billing.com",
        "tescobank-secure-auth.com", config.REPORT_ONLY_DOMAIN,
        "tesco-rewards-login.com",
    }
    min_ap = gold[gold["domain"].isin(ap_domains)]["risk_score"].min()
    for ce in ("tesco-careers-verify.com", config.DECOY_DOMAIN):
        ce_score = gold[gold["domain"] == ce]["risk_score"].iloc[0]
        assert ce_score < min_ap, f"{ce} scored {ce_score} >= min AP {min_ap}"


def test_careers_verify_high_confidence_low_exposure(gold):
    """Confidence is not exposure: highest-confidence domain scores below APs."""
    cv = gold[gold["domain"] == "tesco-careers-verify.com"].iloc[0]
    assert cv["max_source_confidence"] == 95
    assert cv["distinct_users_hit"] == 1


def test_report_only_metric(gold, world):
    m = report_only_metric(gold, world.telemetry.dns)
    assert m["report_only_domains"] == 1
    assert m["report_only_users"] == 2


# ---------------------------------------------------------------------------
# Brand similarity threshold (PLAN 13.1)
# ---------------------------------------------------------------------------
def test_hero_similarity_at_least_85():
    score, _ = brand_similarity(config.HERO_DOMAIN)
    assert score >= 85


def test_unrelated_domain_low_similarity():
    for benign in ("google.com", "microsoft.com", "ransomgate123.xyz"):
        score, _ = brand_similarity(benign)
        assert score < 60, f"{benign} scored {score}"


# ---------------------------------------------------------------------------
# Regex-vs-AI extraction diff (PLAN 7.5, 13.1)
# ---------------------------------------------------------------------------
def test_extraction_diff_has_ai_only_recovery(world):
    reports_pdf = pd.DataFrame([
        {"report_id": r.report_id, "body": r.body} for r in world.reports
    ])
    regex = build_silver_iocs_regex(reports_pdf)
    diff = build_extraction_diff(regex, world.gt_report_entities)
    assert has_ai_only_recovery(diff), "no report has an AI-only recovered indicator"


def test_regex_finds_clean_indicators(world):
    reports_pdf = pd.DataFrame([
        {"report_id": r.report_id, "body": r.body} for r in world.reports
    ])
    regex = build_silver_iocs_regex(reports_pdf)
    # The FreshCart reports carry clean URLs regex should catch.
    fc = regex[regex["report_id"].isin(["R01", "R03", "R05"])]
    assert len(fc) > 0


# ---------------------------------------------------------------------------
# Feed parse + dedup (PLAN 7.4)
# ---------------------------------------------------------------------------
def test_feed_dedup_collapses_overlap(world):
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        write_misp_events(world.iocs, base / "misp", world.reference_ts)
        write_stix_bundle(world.iocs, base / "stix", world.reference_ts)
        write_csv_feed(world.iocs, base / "csv", world.reference_ts)
        silver = build_silver_iocs(base / "misp", base / "stix", base / "csv")

    # silver_iocs is deduped: each (value, type) appears once.
    assert silver.duplicated(["indicator_value", "indicator_type"]).sum() == 0
    # Some IOCs are multi-source (the A-URL overlap between MISP and CSV).
    assert (silver["source_count"] >= 2).any()
