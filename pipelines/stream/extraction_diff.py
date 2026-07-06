"""Regex-vs-agent extraction diff (PLAN 7.5), the Act 1 contrast beat.

For each report, computes regex_only, ai_only, and both indicator sets, plus
the AI-only entity types (TTPs, brands, kits) regex structurally cannot
produce. The hero report set makes it vivid: regex gets the clean domains, the
agent additionally gets the defanged and prose-described ones.

The AI side is represented by the per-report ground-truth entities (what a
correct extraction agent recovers). The live pipeline swaps in the Agent Bricks
extraction output; this reference build uses ground truth so the diff is exact.
"""

from __future__ import annotations

import pandas as pd

DIFF_COLS = ["report_id", "regex_only", "ai_only", "both", "ai_only_entity_types"]


def build_extraction_diff(
    silver_iocs_regex: pd.DataFrame,
    gt_report_entities: pd.DataFrame,
) -> pd.DataFrame:
    """Return the per-report regex-vs-AI diff table.

    silver_iocs_regex: report_id, indicator_value (from ioc_regex).
    gt_report_entities: report_id, entity_kind, value (the AI target).
    """
    regex_by_report: dict[str, set[str]] = {}
    for rid, grp in silver_iocs_regex.groupby("report_id"):
        regex_by_report[rid] = set(grp["indicator_value"])

    rows = []
    for rid, grp in gt_report_entities.groupby("report_id"):
        ai_iocs = set(grp.loc[grp["entity_kind"] == "ioc", "value"])
        regex_iocs = regex_by_report.get(rid, set())
        # Non-IOC entity kinds only the AI pass produces.
        ai_entity_types = sorted(set(
            grp.loc[grp["entity_kind"] != "ioc", "entity_kind"]
        ))
        rows.append({
            "report_id": rid,
            "regex_only": sorted(regex_iocs - ai_iocs),
            "ai_only": sorted(ai_iocs - regex_iocs),
            "both": sorted(ai_iocs & regex_iocs),
            "ai_only_entity_types": ai_entity_types,
        })
    return pd.DataFrame(rows, columns=DIFF_COLS)


def has_ai_only_recovery(diff: pd.DataFrame) -> bool:
    """True if at least one report has an AI-only indicator regex missed.

    The PLAN 13.1 assert: the diff must yield a non-empty ai_only set for at
    least one report where the agent recovers a defanged or prose-described
    indicator the regex pass missed.
    """
    return any(len(r) > 0 for r in diff["ai_only"])
