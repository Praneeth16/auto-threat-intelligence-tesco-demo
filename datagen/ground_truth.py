"""Consolidated ground-truth tables and the world builder.

build_world() is the single entry point: it computes REFERENCE_TS, builds every
entity/campaign/telemetry/report/filler artifact from the seeded RNG, and
returns them alongside the ground-truth tables the validation suite and demo
depend on.

Ground truth is authored here (gt_campaigns, gt_attack_paths,
gt_expected_findings, gt_report_entities, gt_filler_labels). The demo's every
detection, score, and agent decision must be rediscoverable from these.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from datagen import config
from datagen.campaigns import CampaignUniverse, build_campaign_universe
from datagen.entities import build_brand_assets, build_employees
from datagen.feeds import build_overlap_pairs
from datagen.filler import build_filler_pool
from datagen.reports import build_reports
from datagen.telemetry import build_telemetry


def reference_ts() -> pd.Timestamp:
    """Anchor for all offsets: the top of the current hour, tz-naive.

    Deterministic given a fixed clock; the demo re-anchors on load so recency
    reads live. Tests pin a fixed value via build_world(anchor=...).
    """
    return pd.Timestamp.now("UTC").floor("h").tz_localize(None)


@dataclass
class World:
    reference_ts: pd.Timestamp
    employees: pd.DataFrame
    brand_assets: pd.DataFrame
    iocs: pd.DataFrame  # structured IOC universe (455)
    ioc_enrichment: pd.DataFrame  # ref_ioc_enrichment (A-C)
    overlap_pairs: pd.DataFrame
    telemetry: object  # datagen.telemetry.Telemetry
    reports: list  # list[datagen.reports.Report]
    filler_pool: pd.DataFrame
    # Ground-truth tables
    gt_campaigns: pd.DataFrame
    gt_attack_paths: pd.DataFrame
    gt_expected_findings: pd.DataFrame
    gt_report_entities: pd.DataFrame
    gt_filler_labels: pd.DataFrame
    benign_domains: list = field(default_factory=list)


def _benign_domains(n: int = 1000) -> list[str]:
    """~1,000 popular-domain vocabulary for benign traffic (PLAN 5.6)."""
    base = [
        "google.com", "microsoft.com", "office.com", "github.com", "slack.com",
        "salesforce.com", "workday.com", "servicenow.com", "atlassian.net",
        "zoom.us", "linkedin.com", "bbc.co.uk", "gov.uk", "amazon.co.uk",
        "cloudflare.com", "apple.com", "adobe.com", "dropbox.com", "notion.so",
        "wikipedia.org",
    ]
    out = list(base)
    i = 0
    # Pad deterministically to n with numbered subdomains of the base set.
    while len(out) < n:
        out.append(f"cdn{i}.{base[i % len(base)]}")
        i += 1
    return out[:n]


def _gt_campaigns() -> pd.DataFrame:
    rows = []
    for c in config.CAMPAIGNS:
        rows.append({
            "campaign_id": c.campaign_id,
            "name": c.name,
            "theme": c.theme,
            "ioc_count": c.ioc_count,
            "asn_label": c.asn_label,
            "registrar": c.registrar,
            "registrant_email": c.registrant_email,
            "kit_id": c.kit_id,
        })
    return pd.DataFrame(rows)


def _gt_attack_paths(evidence: dict) -> pd.DataFrame:
    """Expected evidence counts per attack path (PLAN 5.4)."""
    rows = [
        {"path_id": "AP1", "domain": config.HERO_DOMAIN,
         "expected_clickers": config.AP1_CLICKERS,
         "expected_cred_posts": config.AP1_CREDENTIAL_SUBMITTERS,
         "expected_failed_bursts": config.AP1_CREDENTIAL_SUBMITTERS,
         "priya_ro_success": True, "expected_rank": 1},
        {"path_id": "AP2", "domain": "tesco-supplier-billing.com",
         "expected_clickers": 1, "expected_cred_posts": 1,
         "expected_failed_bursts": 0, "priya_ro_success": False,
         "expected_rank": 2},
        {"path_id": "AP3", "domain": config.REPORT_ONLY_DOMAIN,
         "expected_clickers": 0, "expected_cred_posts": 0,
         "expected_failed_bursts": 0, "priya_ro_success": False,
         "expected_rank": None, "dns_employees": 2},
        {"path_id": "AP4", "domain": "tescobank-secure-auth.com",
         "expected_clickers": 0, "expected_cred_posts": 0,
         "expected_failed_bursts": 0, "priya_ro_success": False,
         "expected_rank": 3},
        {"path_id": "AP5", "domain": "tesco-rewards-login.com",
         "expected_clickers": 0, "expected_cred_posts": 0,
         "expected_failed_bursts": 0, "priya_ro_success": False,
         "expected_rank": 5, "visits": config.AP5_VISITS},
    ]
    return pd.DataFrame(rows)


def _gt_expected_findings() -> pd.DataFrame:
    """Expected top-5 domains in rank order (PLAN 5.6, 13.1). Hero is #1."""
    rows = [
        {"rank": 1, "domain": config.HERO_DOMAIN, "tolerance": 0},
        {"rank": 2, "domain": "tesco-supplier-billing.com", "tolerance": 1},
        {"rank": 3, "domain": "tescobank-secure-auth.com", "tolerance": 1},
        {"rank": 4, "domain": config.REPORT_ONLY_DOMAIN, "tolerance": 1},
        {"rank": 5, "domain": "tesco-rewards-login.com", "tolerance": 1},
    ]
    return pd.DataFrame(rows)


def _gt_report_entities(reports: list) -> pd.DataFrame:
    """Flatten per-report ground truth into rows for recall scoring."""
    rows = []
    for rep in reports:
        gt = rep.ground_truth
        for ioc in gt["iocs"]:
            rows.append({
                "report_id": rep.report_id,
                "entity_kind": "ioc",
                "value": ioc["value"],
                "type": ioc["type"],
            })
        for actor in gt["actors"]:
            rows.append({"report_id": rep.report_id, "entity_kind": "actor",
                         "value": actor, "type": "actor"})
        for ttp in gt["ttps"]:
            rows.append({"report_id": rep.report_id, "entity_kind": "ttp",
                         "value": ttp, "type": "ttp"})
        for brand in gt["targeted_brands"]:
            rows.append({"report_id": rep.report_id, "entity_kind": "brand",
                         "value": brand, "type": "brand"})
        for kit in gt["kit_ids"]:
            rows.append({"report_id": rep.report_id, "entity_kind": "kit",
                         "value": kit, "type": "kit"})
    return pd.DataFrame(rows)


def _gt_filler_labels(filler_pool: pd.DataFrame) -> pd.DataFrame:
    return filler_pool[
        ["filler_id", "category", "ground_truth_label", "expected_route"]
    ].copy()


def build_world(anchor: pd.Timestamp | None = None) -> World:
    """Build the entire synthetic world deterministically.

    anchor pins REFERENCE_TS for reproducible tests; production load uses the
    live top-of-hour so recency reads correctly on demo day.
    """
    ref = anchor if anchor is not None else reference_ts()

    employees = build_employees()
    brand_assets = build_brand_assets()
    universe: CampaignUniverse = build_campaign_universe()
    overlap = build_overlap_pairs(universe.iocs)
    benign = _benign_domains()
    telem = build_telemetry(employees, benign, ref)
    reports = build_reports()
    filler_pool = build_filler_pool()

    return World(
        reference_ts=ref,
        employees=employees,
        brand_assets=brand_assets,
        iocs=universe.iocs,
        ioc_enrichment=universe.enrichment,
        overlap_pairs=overlap,
        telemetry=telem,
        reports=reports,
        filler_pool=filler_pool,
        gt_campaigns=_gt_campaigns(),
        gt_attack_paths=_gt_attack_paths(telem.attack_evidence),
        gt_expected_findings=_gt_expected_findings(),
        gt_report_entities=_gt_report_entities(reports),
        gt_filler_labels=_gt_filler_labels(filler_pool),
        benign_domains=benign,
    )
