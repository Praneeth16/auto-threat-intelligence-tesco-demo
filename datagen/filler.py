"""The filler pool: ~120 labeled template events that power "keep generating".

Each item carries a ground-truth label and the lane the policy router should
send it to. datagen/tests asserts every item's label matches its expected
route, so sampling at demo time is safe.

The clubcard-summer/autumn pair is director-injected (not sampled) and lives in
config/ground_truth, not here, so the Act 4 policy-exception beat stays
scripted.
"""

from __future__ import annotations

import pandas as pd

from datagen import config
from datagen.common import rng

_COMMODITY_WORDS = ["login-alert", "account-verify", "secure-update", "mailbox-full",
                    "password-expiry", "invoice-view", "docusign-review"]
_SCANNER_NOTES = ["masscan probe", "shodan crawl", "http OPTIONS sweep",
                  "tcp SYN scan", "path traversal probe"]
_TLDS = [".com", ".net", ".info", ".xyz", ".top", ".click"]


def build_filler_pool() -> pd.DataFrame:
    """Return the filler pool (PLAN 5.5) with ground-truth labels and routes."""
    r = rng("filler")
    rows = []
    used = set()

    def uniq_domain(word_pool):
        for _ in range(200):
            w = r.choice(word_pool)
            d = f"{w}-{r.randint(100, 9999)}{r.choice(_TLDS)}"
            if d not in used:
                used.add(d)
                return d
        raise RuntimeError("filler domain generator exhausted")

    for cat in config.FILLER_CATEGORIES:
        for i in range(cat.count):
            if cat.name == "commodity_phish":
                # Exact known-bad IOC match: carries an exact_ioc_match flag.
                event = {
                    "kind": "proxy",
                    "domain": uniq_domain(_COMMODITY_WORDS),
                    "exact_ioc_match": True,
                    "brand_similarity": r.randint(0, 30),
                    "corroboration": "high",
                    "note": "known-bad commodity phish",
                }
            elif cat.name == "scanner_recon":
                event = {
                    "kind": "scanner",
                    "domain": None,
                    "exact_ioc_match": False,
                    "brand_similarity": 0,
                    "corroboration": "none",
                    "note": r.choice(_SCANNER_NOTES),
                }
            elif cat.name == "known_false_positive":
                event = {
                    "kind": "proxy",
                    "domain": uniq_domain(_COMMODITY_WORDS),
                    "exact_ioc_match": False,
                    "brand_similarity": r.randint(0, 20),
                    "corroboration": "duplicate",
                    "note": "duplicate of prior benign disposition",
                }
            else:  # ambiguous_lookalike
                event = {
                    "kind": "proxy",
                    "domain": uniq_domain(["tesco", "clubcard"]),
                    "exact_ioc_match": False,
                    "brand_similarity": r.randint(60, 84),
                    "corroboration": "low",
                    "note": "ambiguous lookalike, low corroboration",
                }
            event.update({
                "filler_id": f"F{len(rows) + 1:04d}",
                "category": cat.name,
                "ground_truth_label": cat.ground_truth_label,
                "expected_route": cat.expected_route,
            })
            rows.append(event)

    cols = ["filler_id", "category", "kind", "domain", "exact_ioc_match",
            "brand_similarity", "corroboration", "note",
            "ground_truth_label", "expected_route"]
    return pd.DataFrame(rows, columns=cols)


def route_filler(event: dict) -> str:
    """Deterministic reference router for a filler event (PLAN 5.5 / 8.4).

    This mirrors the policy_router lanes so datagen/tests can assert each
    pool item routes where its label expects. The real router (Stage 5) reads
    policy_store; this is the labeling oracle.
    """
    # Scanner / recon noise -> pre-filter close.
    if event["kind"] == "scanner":
        return "prefilter_close"
    # Known duplicate benign -> pre-filter close (dedup).
    if event["corroboration"] == "duplicate":
        return "prefilter_close"
    # Exact known-bad IOC match -> tier-0 auto close (watchlist), no agent.
    if event["exact_ioc_match"]:
        return "tier0_auto_close"
    # Ambiguous lookalike, low corroboration -> agent triages, queue.
    if event["brand_similarity"] >= 60 and event["corroboration"] == "low":
        return "agent_queue"
    # Anything else falls through to the agent queue for safety.
    return "agent_queue"
