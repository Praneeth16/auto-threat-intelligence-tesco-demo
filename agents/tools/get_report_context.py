"""get_report_context(domain) -> matching rows from silver_report_entities /
silver_report_summaries (PLAN 8.3).

A structured lookup over already-extracted report content: no Vector Search
index needed, because Layer 3 extraction already turned the reports into
queryable tables. This is how the agent cites report evidence for a domain,
including the feed-gap domain that appears only in R14.
"""

from __future__ import annotations

import pandas as pd


def get_report_context(domain: str, report_entities: pd.DataFrame) -> dict:
    """Return the reports and entity kinds that mention a domain."""
    hits = report_entities[report_entities["value"] == domain]
    reports = sorted(set(hits["report_id"]))
    # Sibling entities co-mentioned in the same reports (actors, ttps, brands).
    context = report_entities[report_entities["report_id"].isin(reports)]
    ttps = sorted(set(context.loc[context["entity_kind"] == "ttp", "value"]))
    actors = sorted(set(context.loc[context["entity_kind"] == "actor", "value"]))
    brands = sorted(set(context.loc[context["entity_kind"] == "brand", "value"]))
    return {
        "domain": domain,
        "reports": reports,
        "report_only": len(reports) > 0,
        "ttps": ttps,
        "actors": actors,
        "targeted_brands": brands,
    }
