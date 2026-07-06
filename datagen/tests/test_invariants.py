"""Invariant tests: assert every PLAN Section 5 payoff.

This is the Stage 1 gate (PLAN 1.1): pytest datagen/tests green. The world is
built once with a fixed anchor so timestamp assertions are deterministic.
"""

from __future__ import annotations

import pandas as pd
import pytest

from datagen import config
from datagen.common import defang, rng
from datagen.filler import route_filler
from datagen.ground_truth import build_world

# Fixed anchor so T-offsets land on known instants.
ANCHOR = pd.Timestamp("2026-07-06 00:00:00")


@pytest.fixture(scope="module")
def world():
    return build_world(anchor=ANCHOR)


@pytest.fixture(scope="module")
def world2():
    # Second independent build for determinism comparison.
    return build_world(anchor=ANCHOR)


# ---------------------------------------------------------------------------
# Determinism (PLAN Section 0, rule 2)
# ---------------------------------------------------------------------------
def test_determinism_employees(world, world2):
    pd.testing.assert_frame_equal(world.employees, world2.employees)


def test_determinism_iocs(world, world2):
    pd.testing.assert_frame_equal(world.iocs, world2.iocs)


def test_determinism_telemetry(world, world2):
    pd.testing.assert_frame_equal(world.telemetry.dns, world2.telemetry.dns)
    pd.testing.assert_frame_equal(world.telemetry.proxy, world2.telemetry.proxy)
    pd.testing.assert_frame_equal(world.telemetry.auth, world2.telemetry.auth)
    pd.testing.assert_frame_equal(world.telemetry.email, world2.telemetry.email)


# ---------------------------------------------------------------------------
# Employees (PLAN 5.3)
# ---------------------------------------------------------------------------
def test_employee_count(world):
    assert len(world.employees) == config.N_EMPLOYEES


def test_privileged_and_vip_counts(world):
    assert int(world.employees["is_privileged"].sum()) == config.N_PRIVILEGED
    assert int(world.employees["is_vip"].sum()) == config.N_VIP


def test_named_characters_exact(world):
    e = world.employees.set_index("employee_id")
    priya = e.loc["E0001"]
    assert priya["full_name"] == "Priya Nair"
    assert priya["is_privileged"]
    assert "Cloud-Admins" in priya["ad_groups"]
    assert priya["usual_country"] == "IN"

    mark = e.loc["E0002"]
    assert mark["full_name"] == "Mark Whitfield"
    assert not mark["is_privileged"]  # deliberately not privileged

    sophie = e.loc["E0003"]
    assert sophie["full_name"] == "Sophie Clarke"
    assert sophie["office_location"] == "Dundee"


def test_email_domain_and_uniqueness(world):
    emails = world.employees["email"]
    assert emails.is_unique
    assert emails.str.endswith(f"@{config.EMPLOYEE_EMAIL_DOMAIN}").all()
    # Never @tesco.com for synthetic people.
    assert not emails.str.contains("@tesco.com").any()


# ---------------------------------------------------------------------------
# Campaign universe (PLAN 5.2)
# ---------------------------------------------------------------------------
def test_total_structured_iocs(world):
    # 455: A(120)+B(60)+C(45)+N(200)+X(30).
    counts = world.iocs["campaign_id"].value_counts()
    assert counts["A"] == 120
    assert counts["B"] == 60
    assert counts["C"] == 45
    assert counts["N"] == config.N_NOISE_IOCS
    assert counts["X"] == config.N_DECOY_DOMAINS
    assert len(world.iocs) == config.TOTAL_STRUCTURED_IOCS


def test_named_domains_exist(world):
    values = set(world.iocs["indicator_value"])
    for d in (config.CAMPAIGN_A_NAMED_DOMAINS + config.CAMPAIGN_B_NAMED_DOMAINS
              + config.CAMPAIGN_C_NAMED_DOMAINS):
        assert d in values, f"named domain missing: {d}"
    assert config.DECOY_DOMAIN in values


def test_report_only_domain_absent_from_structured_feeds(world):
    # AP3 feed-gap [exact]: in no structured feed.
    assert config.REPORT_ONLY_DOMAIN not in set(world.iocs["indicator_value"])


def test_ioc_values_unique(world):
    assert world.iocs["indicator_value"].is_unique


def test_enrichment_populated_for_campaigns_only(world):
    enr = world.ioc_enrichment
    # A-C indicators have enrichment; N/X have none in the table.
    campaign_vals = set(
        world.iocs[world.iocs["campaign_id"].isin(["A", "B", "C"])]["indicator_value"]
    )
    assert set(enr["indicator_value"]).issubset(campaign_vals)
    # Every enrichment row has an ASN label (non-null).
    assert enr["asn_label"].notna().all()


def test_feed_overlap_present(world):
    # ~10% of cluster IOCs planted in two feeds (dedup target).
    assert len(world.overlap_pairs) > 0


# ---------------------------------------------------------------------------
# AP1 hero invariants (PLAN 5.4, 13.1)
# ---------------------------------------------------------------------------
def test_ap1_email_wave(world):
    email = world.telemetry.email
    wave = email[(email["sender"] == config.AP1_SENDER)
                 & (email["subject"] == config.AP1_EMAIL_SUBJECT)
                 & (email["action"] == "delivered")]
    assert wave["employee_id"].nunique() == config.AP1_EMAIL_RECIPIENTS


def test_ap1_seventeen_distinct_clickers(world):
    email = world.telemetry.email
    clicks = email[(email["subject"] == config.AP1_EMAIL_SUBJECT)
                   & (email["action"] == "clicked")]
    assert clicks["employee_id"].nunique() == config.AP1_CLICKERS


def test_ap1_three_credential_posts(world):
    proxy = world.telemetry.proxy
    posts = proxy[(proxy["domain"] == config.HERO_DOMAIN)
                  & (proxy["method"] == "POST")]
    assert posts["employee_id"].nunique() == config.AP1_CREDENTIAL_SUBMITTERS
    # ~200-400 bytes up.
    assert posts["bytes_out"].between(200, 400).all()


def test_ap1_failed_login_bursts_in_window(world):
    """Each of the 3 submitters shows 5-8 failures 20-45 min after click."""
    proxy = world.telemetry.proxy
    auth = world.telemetry.auth
    email = world.telemetry.email

    submitters = set(
        proxy[(proxy["domain"] == config.HERO_DOMAIN) & (proxy["method"] == "POST")]["employee_id"]
    )
    assert len(submitters) == 3

    clicks = email[(email["subject"] == config.AP1_EMAIL_SUBJECT)
                   & (email["action"] == "clicked")]
    click_by_emp = clicks.groupby("employee_id")["ts"].min()

    for emp in submitters:
        click_ts = click_by_emp[emp]
        fails = auth[(auth["employee_id"] == emp) & (auth["result"] == "failure")]
        # Failures within 20-45 min (plus the burst length) of the click.
        window = fails[(fails["ts"] >= click_ts + pd.Timedelta(minutes=20))
                       & (fails["ts"] <= click_ts + pd.Timedelta(minutes=60))]
        assert config.AP1_FAILED_LOGIN_MIN <= len(window) <= config.AP1_FAILED_LOGIN_MAX
        # A lockout follows.
        lockouts = auth[(auth["employee_id"] == emp) & (auth["result"] == "lockout")]
        assert len(lockouts) >= 1


def test_ap1_priya_ro_success(world):
    auth = world.telemetry.auth
    priya = auth[(auth["employee_id"] == "E0001")
                 & (auth["result"] == "success")
                 & (auth["country"] == config.AP1_PRIYA_SUCCESS_COUNTRY)]
    assert len(priya) == 1
    row = priya.iloc[0]
    assert row["asn_label"] == config.AP1_PRIYA_SUCCESS_ASN
    assert row["device"] == "unknown"
    # T-1 22:37.
    expected = ANCHOR - pd.Timedelta(days=1) + pd.Timedelta(hours=22, minutes=37)
    assert row["ts"] == expected


# ---------------------------------------------------------------------------
# AP2/AP3/AP4/AP5 (PLAN 5.4)
# ---------------------------------------------------------------------------
def test_ap2_bec(world):
    proxy = world.telemetry.proxy
    auth = world.telemetry.auth
    posts = proxy[(proxy["domain"] == "tesco-supplier-billing.com")
                  & (proxy["method"] == "POST")]
    assert set(posts["employee_id"]) == {"E0002"}
    ro = auth[(auth["employee_id"] == "E0002") & (auth["country"] == "RO")
              & (auth["result"] == "success")]
    assert len(ro) == 1


def test_ap3_feed_gap_dns(world):
    dns = world.telemetry.dns
    hits = dns[dns["query_domain"] == config.REPORT_ONLY_DOMAIN]
    assert hits["employee_id"].nunique() == 2
    # Present in bronze DNS, absent from structured feeds (checked above).


def test_ap4_fresh_dns(world):
    dns = world.telemetry.dns
    hits = dns[dns["query_domain"] == "tescobank-secure-auth.com"]
    # 3 users at T-1, 1 user at T-0 = 4 distinct.
    assert hits["employee_id"].nunique() == 4


def test_ap5_nine_visits(world):
    proxy = world.telemetry.proxy
    visits = proxy[(proxy["domain"] == "tesco-rewards-login.com")
                   & (proxy["employee_id"] == "E0003")]
    assert len(visits) == config.AP5_VISITS


def test_counterexample_careers_verify(world):
    dns = world.telemetry.dns
    hits = dns[dns["query_domain"] == "tesco-careers-verify.com"]
    assert len(hits) == config.CAREERS_VERIFY_DNS_HITS
    assert (hits["source_tag"] == "guest-wifi").all()


def test_counterexample_fans_forum(world):
    proxy = world.telemetry.proxy
    visits = proxy[proxy["domain"] == config.DECOY_DOMAIN]
    assert visits["employee_id"].nunique() == config.FANS_FORUM_VISITS


def test_noise_iocs_zero_internal_hits(world):
    """200 noise IOCs never appear in internal telemetry."""
    noise_domains = set(
        world.iocs[(world.iocs["campaign_id"] == "N")
                   & (world.iocs["indicator_type"] == "domain")]["indicator_value"]
    )
    dns_domains = set(world.telemetry.dns["query_domain"])
    proxy_domains = set(world.telemetry.proxy["domain"])
    assert noise_domains.isdisjoint(dns_domains)
    assert noise_domains.isdisjoint(proxy_domains)


# ---------------------------------------------------------------------------
# Bronze row counts (PLAN 5.6, within +/-2%)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table,target", [
    ("dns", config.BRONZE_DNS_ROWS),
    ("proxy", config.BRONZE_PROXY_ROWS),
    ("email", config.BRONZE_EMAIL_ROWS),
    ("auth", config.BRONZE_AUTH_ROWS),
])
def test_bronze_row_counts(world, table, target):
    df = getattr(world.telemetry, table)
    lo = target * (1 - config.ROW_COUNT_TOLERANCE)
    hi = target * (1 + config.ROW_COUNT_TOLERANCE)
    assert lo <= len(df) <= hi, f"{table}={len(df)} outside {lo:.0f}..{hi:.0f}"


# ---------------------------------------------------------------------------
# Reports (PLAN 5.7)
# ---------------------------------------------------------------------------
def test_report_count_and_ids(world):
    ids = [r.report_id for r in world.reports]
    assert len(ids) == config.N_REPORTS
    assert set(ids) == set(config.REPORT_IDS)


def test_r14_feed_gap_content(world):
    r14 = next(r for r in world.reports if r.report_id == "R14")
    # Contains the report-only domain + the exact IP, both defanged in body.
    assert defang(config.REPORT_ONLY_DOMAIN) in r14.body
    assert defang(config.R14_IP) in r14.body
    # Ground truth carries them plain for matching.
    gt_vals = {i["value"] for i in r14.ground_truth["iocs"]}
    assert config.REPORT_ONLY_DOMAIN in gt_vals
    assert config.R14_IP in gt_vals


def test_r15_exclusive_quiet(world):
    r15 = next(r for r in world.reports if r.report_id == "R15")
    gt_vals = {i["value"] for i in r15.ground_truth["iocs"]}
    # A sender and a URL, neither in feeds nor telemetry.
    assert any(v.startswith("notices@") for v in gt_vals)
    feed_vals = set(world.iocs["indicator_value"])
    for v in gt_vals:
        assert v not in feed_vals


def test_noise_reports_no_brand_relevance(world):
    for rid in ("R19", "R20"):
        rep = next(r for r in world.reports if r.report_id == rid)
        assert rep.ground_truth["targeted_brands"] == []


def test_defanged_reports_have_no_plain_hero(world):
    """R02/R04 are fully defanged: no bare hero domain in the body."""
    for rid in ("R02", "R04"):
        rep = next(r for r in world.reports if r.report_id == rid)
        # The hero appears only in defanged form.
        assert config.HERO_DOMAIN not in rep.body
        assert defang(config.HERO_DOMAIN) in rep.body


# ---------------------------------------------------------------------------
# Filler pool routing (PLAN 5.5)
# ---------------------------------------------------------------------------
def test_filler_pool_size(world):
    assert len(world.filler_pool) == config.FILLER_POOL_SIZE


def test_every_filler_routes_to_expected_lane(world):
    pool = world.filler_pool
    for _, row in pool.iterrows():
        actual = route_filler(row.to_dict())
        assert actual == row["expected_route"], (
            f"{row['filler_id']} ({row['category']}): "
            f"routed {actual}, expected {row['expected_route']}"
        )


# ---------------------------------------------------------------------------
# defang() helper (PLAN Section 0, rule 5)
# ---------------------------------------------------------------------------
def test_defang_basic():
    assert defang("tesco-clubcard-support.com") == "tesco-clubcard-support[.]com"
    assert defang("https://evil.com/path") == "hxxps://evil[.]com/path"


def test_defang_idempotent():
    once = defang("tesco-clubcard-support.com")
    assert defang(once) == once


# ---------------------------------------------------------------------------
# Ground-truth tables present
# ---------------------------------------------------------------------------
def test_gt_expected_findings_hero_first(world):
    gt = world.gt_expected_findings.sort_values("rank")
    assert gt.iloc[0]["domain"] == config.HERO_DOMAIN
    assert gt.iloc[0]["rank"] == 1


def test_gt_campaigns_three(world):
    assert len(world.gt_campaigns) == 3


def test_reference_ts_is_top_of_hour():
    from datagen.ground_truth import reference_ts
    ts = reference_ts()
    assert ts.minute == 0 and ts.second == 0 and ts.microsecond == 0
