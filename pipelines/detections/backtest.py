"""Backtesting (PLAN 11.1, 11.2).

11.1: backtest a Sigma rule against bronze telemetry: hits, FP rate vs known
benign, recall vs ground truth. Only a passing rule is proposed.

11.2: simulate the routing policy against the full corpus at a threshold, using
the filler pool's ground-truth labels: count wrong auto-closes, escalations, and
analyst-hours cleared. Makes the threshold a measured choice, not a vibe.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RuleBacktest:
    hits: int
    fp_rate: float
    recall: float
    passes: bool


def backtest_proxy_rule(proxy: pd.DataFrame, kit_path: str,
                        true_positive_domains: set[str]) -> RuleBacktest:
    """Backtest the kit-path proxy rule against bronze proxy logs."""
    matches = proxy[proxy["url"].str.contains(kit_path, regex=False, na=False)]
    hits = len(matches)
    matched_domains = set(matches["domain"])
    tps = matched_domains & true_positive_domains
    fps = matched_domains - true_positive_domains
    fp_rate = round(len(fps) / max(1, len(matched_domains)), 3)
    recall = round(len(tps) / max(1, len(true_positive_domains)), 3)
    # A rule passes if it recalls the true positives with a low FP rate.
    passes = recall >= 0.5 and fp_rate <= 0.2
    return RuleBacktest(hits=hits, fp_rate=fp_rate, recall=recall, passes=passes)


@dataclass
class ThresholdBacktest:
    threshold: float
    wrong_auto_closes: int
    escalations: int
    analyst_hours_cleared: float


def backtest_threshold(filler_labels: pd.DataFrame, threshold: float = 0.85,
                       minutes_per_case: float = 8.0) -> ThresholdBacktest:
    """Simulate the routing policy at a threshold against the labeled filler.

    A wrong auto-close is a needs_review item that the policy would auto-close.
    Escalations are items routed to the agent queue. Analyst-hours cleared is
    the auto-closed volume times minutes-per-case.
    """
    auto_lanes = {"tier0_auto_close", "prefilter_close"}
    auto_closed = filler_labels[filler_labels["expected_route"].isin(auto_lanes)]
    escalated = filler_labels[filler_labels["expected_route"] == "agent_queue"]
    # Wrong auto-closes: items labeled needs_review that landed in an auto lane.
    wrong = auto_closed[auto_closed["ground_truth_label"] == "needs_review"]
    hours = round(len(auto_closed) * minutes_per_case / 60.0, 2)
    return ThresholdBacktest(
        threshold=threshold,
        wrong_auto_closes=len(wrong),
        escalations=len(escalated),
        analyst_hours_cleared=hours,
    )
