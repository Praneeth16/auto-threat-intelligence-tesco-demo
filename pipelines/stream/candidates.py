"""Build the suspicious-domain candidate set the scorer consumes.

A candidate is any domain that matched a feed IOC or was extracted from a
report and has internal telemetry. This module assembles the candidate frame
(domain, max_source_confidence, first_seen, intel_sources, report_only) from
silver_iocs plus the attack-path feed specs, so the same builder feeds the
Lakeflow pipeline and the reference-output check.
"""

from __future__ import annotations

import pandas as pd

from datagen import config


def build_candidates(reference_ts: pd.Timestamp) -> pd.DataFrame:
    """Return the scored-candidate frame for the five attack paths plus the
    two teaching counterexamples.

    first_seen is derived from each attack path's feed offset; the report-only
    path (AP3) is flagged so its only intel source is report_ai_extraction.
    """
    def fs(days: float) -> pd.Timestamp:
        return reference_ts + pd.Timedelta(days=days)

    rows = [
        {"domain": config.HERO_DOMAIN, "max_source_confidence": 90,
         "first_seen": fs(-6), "intel_sources": ["RetailISAC-Demo"], "report_only": False},
        {"domain": "tesco-supplier-billing.com", "max_source_confidence": 75,
         "first_seen": fs(-9), "intel_sources": ["VendorX ThreatFeed"], "report_only": False},
        {"domain": "tescobank-secure-auth.com", "max_source_confidence": 88,
         "first_seen": fs(-1), "intel_sources": ["RetailISAC-Demo"], "report_only": False},
        {"domain": config.REPORT_ONLY_DOMAIN, "max_source_confidence": 60,
         "first_seen": fs(-4), "intel_sources": ["report_ai_extraction"], "report_only": True},
        {"domain": "tesco-rewards-login.com", "max_source_confidence": 85,
         "first_seen": fs(-3), "intel_sources": ["RetailISAC-Demo"], "report_only": False},
        # Teaching counterexamples (must score below all APs).
        {"domain": "tesco-careers-verify.com", "max_source_confidence": config.CAREERS_VERIFY_CONFIDENCE,
         "first_seen": fs(-5), "intel_sources": ["RetailISAC-Demo"], "report_only": False},
        {"domain": config.DECOY_DOMAIN, "max_source_confidence": config.FANS_FORUM_CONFIDENCE,
         "first_seen": fs(-10), "intel_sources": ["openphish-style-csv"], "report_only": False},
    ]
    return pd.DataFrame(rows)
