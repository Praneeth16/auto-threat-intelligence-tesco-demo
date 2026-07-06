"""Classical enrichment features (PLAN 7.4).

Joins registrar, ASN label, and resolved hosting IP from ref_ioc_enrichment
(the stand-in for WHOIS/passive-DNS/ASN services) and emits three derived
flags the risk score and the AI prompt consume:
  is_recent_registration, shared_hosting_flag, asn_reputation_bucket.

No external APIs; all lookups resolve against generator-provided reference
tables. Populated for campaigns A-C, null for noise/decoys.
"""

from __future__ import annotations

import pandas as pd

# ASN labels that read as bulletproof/low-reputation hosting in the demo world.
_BAD_ASN_MARKERS = ("BulletHost", "FastFlux", "CloudCheap", "GreyStack")


def _asn_bucket(asn_label: str | None) -> str:
    if not asn_label:
        return "unknown"
    if any(m in asn_label for m in _BAD_ASN_MARKERS):
        return "bad"
    return "neutral"


def add_enrichment_features(
    domains: pd.DataFrame,
    ioc_enrichment: pd.DataFrame,
    first_seen_days: pd.Series | None = None,
    col: str = "domain",
) -> pd.DataFrame:
    """Left-join enrichment and derive the three score-feeding flags.

    domains: frame with a domain column.
    ioc_enrichment: ref_ioc_enrichment (indicator_value, hosting_ip, asn_label,
                    registrar, registrant_email, kit_id).
    first_seen_days: optional series (days since first seen) aligned to domains;
                     drives is_recent_registration (<=2 days).
    """
    enr = ioc_enrichment.rename(columns={"indicator_value": col})
    out = domains.merge(enr, on=col, how="left")

    out["asn_reputation_bucket"] = out["asn_label"].map(_asn_bucket)

    # shared_hosting_flag: more than one campaign domain on the same hosting IP.
    ip_counts = out.groupby("hosting_ip")[col].transform("count")
    out["shared_hosting_flag"] = (out["hosting_ip"].notna() & (ip_counts > 1)).astype(int)

    # is_recent_registration: first seen within the last 2 days.
    if first_seen_days is not None:
        out["is_recent_registration"] = (first_seen_days.reindex(out.index) <= 2).fillna(False).astype(int)
    else:
        out["is_recent_registration"] = 0

    return out
