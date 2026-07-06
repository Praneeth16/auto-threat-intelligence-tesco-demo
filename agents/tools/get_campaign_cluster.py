"""get_campaign_cluster(domain) -> cluster id/name and shared-infra evidence
(PLAN 8.3). Reads structured_iocs + ref_ioc_enrichment.
"""

from __future__ import annotations

import pandas as pd


def get_campaign_cluster(
    domain: str,
    iocs: pd.DataFrame,
    ioc_enrichment: pd.DataFrame,
    gt_campaigns: pd.DataFrame,
) -> dict:
    """Return the campaign a domain belongs to plus its shared-infra evidence."""
    row = iocs[iocs["indicator_value"] == domain]
    if row.empty:
        return {"domain": domain, "campaign_id": None, "campaign_name": None,
                "shared_infra": {}}
    cid = row.iloc[0]["campaign_id"]
    camp = gt_campaigns[gt_campaigns["campaign_id"] == cid]
    name = camp.iloc[0]["name"] if not camp.empty else None

    enr = ioc_enrichment[ioc_enrichment["indicator_value"] == domain]
    shared = {}
    if not enr.empty:
        e = enr.iloc[0]
        shared = {
            "hosting_ip": e.get("hosting_ip"),
            "asn_label": e.get("asn_label"),
            "registrar": e.get("registrar"),
            "registrant_email": e.get("registrant_email"),
            "kit_id": e.get("kit_id"),
        }
    # Count co-campaign domains sharing the same registrant email.
    if shared.get("registrant_email"):
        siblings = ioc_enrichment[
            ioc_enrichment["registrant_email"] == shared["registrant_email"]
        ]["indicator_value"].nunique()
    else:
        siblings = 0
    return {
        "domain": domain,
        "campaign_id": cid,
        "campaign_name": name,
        "shared_infra": shared,
        "sibling_indicator_count": int(siblings),
    }
