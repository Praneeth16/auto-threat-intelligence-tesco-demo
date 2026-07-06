"""Feed writers: MISP JSON, STIX 2.1 bundle, CSV.

Renders the structured IOC universe into the three feed formats the room
recognizes. Feed overlap (~10% of cluster IOCs in two feeds at slightly
different confidence) is planted deliberately to force the dedup step.

Cluster D from an earlier plan draft was cut (PLAN 5.2); feeds cover A/B/C plus
noise and decoys. Recorded in BUILD_NOTES.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from datagen import config
from datagen.common import rng

# Feed assignment by campaign (which structured feed carries each cluster).
_MISP_CAMPAIGNS = {"A", "C"}  # RetailISAC-Demo MISP events
_STIX_CAMPAIGNS = {"B"}  # VendorX STIX bundle
_CSV_CAMPAIGNS = {"A"}  # openphish-style CSV (URLs) + decoys


def _reference_ts_iso(reference_ts: pd.Timestamp, offset_days: float) -> str:
    return (reference_ts + pd.Timedelta(days=offset_days)).isoformat()


def _confidence_for(campaign_id: str, r) -> int:
    """Feed confidence per campaign, matching AP specs where they apply."""
    base = {"A": 90, "B": 75, "C": 95, "N": 40, "X": 20}.get(campaign_id, 50)
    # Small jitter so overlapping duplicates differ slightly.
    return max(1, min(100, base + r.randint(-3, 3)))


def write_misp_events(iocs: pd.DataFrame, out_dir: Path, reference_ts: pd.Timestamp) -> list[Path]:
    """Write three MISP event JSON files (loadable by pymisp.MISPEvent)."""
    r = rng("feed_misp")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Attributes: all A and C, plus a slice of noise.
    cluster = iocs[iocs["campaign_id"].isin(_MISP_CAMPAIGNS)]
    noise = iocs[iocs["campaign_id"] == "N"].sample(
        n=min(60, (iocs["campaign_id"] == "N").sum()), random_state=config.SEED
    )
    attrs = pd.concat([cluster, noise], ignore_index=True)

    type_map = {"domain": "domain", "url": "url", "ip": "ip-dst",
                "email": "email-src", "hash": "sha256"}

    # Split attributes across three events.
    chunks = [attrs.iloc[i::3] for i in range(3)]
    paths = []
    for n, chunk in enumerate(chunks, start=1):
        event = {
            "Event": {
                "uuid": f"retailisac-demo-{n:04d}",
                "info": f"RetailISAC-Demo advisory batch {n}",
                "date": _reference_ts_iso(reference_ts, -6)[:10],
                "threat_level_id": "2",
                "analysis": "2",
                "Attribute": [
                    {
                        "type": type_map.get(row["indicator_type"], "text"),
                        "value": row["indicator_value"],
                        "category": "Network activity",
                        "to_ids": True,
                        "comment": f"confidence={_confidence_for(row['campaign_id'], r)}",
                    }
                    for _, row in chunk.iterrows()
                ],
            }
        }
        p = out_dir / f"retailisac_demo_event_{n}.json"
        p.write_text(json.dumps(event, indent=2))
        paths.append(p)
    return paths


def write_stix_bundle(iocs: pd.DataFrame, out_dir: Path, reference_ts: pd.Timestamp) -> Path:
    """Write a valid STIX 2.1 bundle with single-comparison indicator patterns."""
    r = rng("feed_stix")
    out_dir.mkdir(parents=True, exist_ok=True)

    cluster = iocs[iocs["campaign_id"].isin(_STIX_CAMPAIGNS)]
    noise = iocs[iocs["campaign_id"] == "N"].sample(
        n=min(120, (iocs["campaign_id"] == "N").sum()), random_state=config.SEED + 1
    )
    indicators = pd.concat([cluster, noise], ignore_index=True)

    created = _reference_ts_iso(reference_ts, -9)

    def _pattern(row) -> str:
        t = row["indicator_type"]
        v = row["indicator_value"].replace("'", "")
        if t == "domain":
            return f"[domain-name:value = '{v}']"
        if t == "url":
            return f"[url:value = '{v}']"
        if t == "ip":
            return f"[ipv4-addr:value = '{v}']"
        if t == "email":
            return f"[email-addr:value = '{v}']"
        return f"[file:hashes.'SHA-256' = '{v}']"

    objects = []
    for i, (_, row) in enumerate(indicators.iterrows()):
        objects.append({
            "type": "indicator",
            "spec_version": "2.1",
            "id": f"indicator--{i:08d}-0000-4000-8000-vendorxdemo0",
            "created": created,
            "modified": created,
            "name": f"VendorX indicator {row['indicator_value']}",
            "pattern": _pattern(row),
            "pattern_type": "stix",
            "valid_from": created,
            "confidence": _confidence_for(row["campaign_id"], r),
        })

    bundle = {"type": "bundle", "id": "bundle--vendorx-demo-0001", "objects": objects}
    p = out_dir / "vendorx_bundle.json"
    p.write_text(json.dumps(bundle, indent=2))
    return p


def write_csv_feed(iocs: pd.DataFrame, out_dir: Path, reference_ts: pd.Timestamp) -> Path:
    """Write an openphish-style CSV (url, discovered_ts, confidence)."""
    r = rng("feed_csv")
    out_dir.mkdir(parents=True, exist_ok=True)

    # A URLs plus decoy domains as URLs.
    urls = iocs[(iocs["campaign_id"].isin(_CSV_CAMPAIGNS)) & (iocs["indicator_type"] == "url")]
    decoys = iocs[iocs["campaign_id"] == "X"]

    rows = []
    for _, row in urls.iterrows():
        rows.append({
            "url": row["indicator_value"],
            "discovered_ts": _reference_ts_iso(reference_ts, -r.randint(1, 8)),
            "confidence": _confidence_for("A", r),
        })
    for _, row in decoys.iterrows():
        rows.append({
            "url": f"https://{row['indicator_value']}/",
            "discovered_ts": _reference_ts_iso(reference_ts, -r.randint(1, 20)),
            "confidence": _confidence_for("X", r),
        })

    df = pd.DataFrame(rows, columns=["url", "discovered_ts", "confidence"])
    p = out_dir / "openphish_style.csv"
    df.to_csv(p, index=False)
    return p


def build_overlap_pairs(iocs: pd.DataFrame) -> pd.DataFrame:
    """Return the ~10% cluster IOCs planted in two feeds (dedup target).

    Recorded as ground truth so the dedup step has an expected count.
    """
    r = rng("feed_overlap")
    cluster = iocs[iocs["campaign_id"].isin(["A", "B", "C"])]
    n = int(len(cluster) * config.FEED_OVERLAP_FRACTION)
    picks = cluster.sample(n=n, random_state=config.SEED + 2)
    return picks[["indicator_value", "indicator_type", "campaign_id"]].reset_index(drop=True)
