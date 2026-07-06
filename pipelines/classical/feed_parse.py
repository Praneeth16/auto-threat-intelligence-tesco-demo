"""Feed parsing: STIX 2.1, MISP JSON, and CSV into a normalized silver_iocs.

The classical ingestion the room recognizes (PLAN 7.4). Parses each feed
format, normalizes to a common IOC shape, and dedups the ~10% cross-feed
overlap, keeping the max confidence per (indicator_value, indicator_type).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# Common normalized schema.
SILVER_COLS = ["indicator_value", "indicator_type", "source_name",
               "source_confidence", "report_id"]

# MISP attribute type -> our indicator_type.
_MISP_TYPE = {"domain": "domain", "url": "url", "ip-dst": "ip", "ip-src": "ip",
              "email-src": "email", "email": "email", "sha256": "hash"}


def _confidence_from_comment(comment: str | None) -> int:
    if comment and "confidence=" in comment:
        try:
            return int(comment.split("confidence=")[1].split()[0])
        except (ValueError, IndexError):
            return 50
    return 50


def parse_misp(misp_dir: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(Path(misp_dir).glob("*.json")):
        event = json.loads(f.read_text())
        for a in event["Event"]["Attribute"]:
            itype = _MISP_TYPE.get(a["type"])
            if not itype:
                continue
            rows.append({
                "indicator_value": a["value"],
                "indicator_type": itype,
                "source_name": "RetailISAC-Demo",
                "source_confidence": _confidence_from_comment(a.get("comment")),
                "report_id": None,
            })
    return pd.DataFrame(rows, columns=SILVER_COLS)


def _stix_value(pattern: str) -> tuple[str, str] | None:
    """Extract (value, indicator_type) from a single-comparison STIX pattern."""
    # e.g. "[domain-name:value = 'x']"
    inner = pattern.strip("[]")
    if ":value" not in inner and "hashes" not in inner:
        return None
    obj = inner.split(":")[0].strip()
    val = inner.split("=")[-1].strip().strip("'\"")
    type_map = {"domain-name": "domain", "url": "url", "ipv4-addr": "ip",
                "email-addr": "email", "file": "hash"}
    return val, type_map.get(obj, "unknown")


def parse_stix(stix_dir: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(Path(stix_dir).glob("*.json")):
        bundle = json.loads(f.read_text())
        for obj in bundle.get("objects", []):
            if obj.get("type") != "indicator":
                continue
            parsed = _stix_value(obj.get("pattern", ""))
            if not parsed:
                continue
            val, itype = parsed
            rows.append({
                "indicator_value": val,
                "indicator_type": itype,
                "source_name": "VendorX ThreatFeed",
                "source_confidence": int(obj.get("confidence", 50)),
                "report_id": None,
            })
    return pd.DataFrame(rows, columns=SILVER_COLS)


def parse_csv(csv_dir: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(Path(csv_dir).glob("*.csv")):
        df = pd.read_csv(f)
        for _, r in df.iterrows():
            rows.append({
                "indicator_value": r["url"],
                "indicator_type": "url",
                "source_name": "openphish-style-csv",
                "source_confidence": int(r.get("confidence", 50)),
                "report_id": None,
            })
    return pd.DataFrame(rows, columns=SILVER_COLS)


def dedup(silver: pd.DataFrame) -> pd.DataFrame:
    """Collapse cross-feed duplicates, keeping the max confidence per IOC.

    Records the contributing source count so the dedup step is measurable.
    """
    if silver.empty:
        out = silver.copy()
        out["source_count"] = pd.Series(dtype="int64")
        return out
    grouped = (silver.groupby(["indicator_value", "indicator_type"], as_index=False)
               .agg(source_confidence=("source_confidence", "max"),
                    source_name=("source_name", lambda s: ",".join(sorted(set(s)))),
                    source_count=("source_name", lambda s: s.nunique()),
                    report_id=("report_id", "first")))
    return grouped


def build_silver_iocs(misp_dir: Path, stix_dir: Path, csv_dir: Path) -> pd.DataFrame:
    """Parse all three feeds and dedup into normalized silver_iocs."""
    combined = pd.concat(
        [parse_misp(misp_dir), parse_stix(stix_dir), parse_csv(csv_dir)],
        ignore_index=True,
    )
    return dedup(combined)
