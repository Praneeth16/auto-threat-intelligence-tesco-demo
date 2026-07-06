"""Risk scoring engine (PLAN 7.2). Pure pandas, deterministic.

Assembles one gold finding per suspicious domain from telemetry, feed
confidence, brand similarity, and enrichment, then computes the transparent
risk score with the exact starting weights. This is the demo's heart: replaying
AP1 must produce the hero finding at rank #1 with every component firing except
repeat-access.

The Lakeflow pipeline (enrich_score.py) calls compute_findings on the same
frames so live and reference outputs cannot drift.
"""

from __future__ import annotations

import math

import pandas as pd

from datagen import config
from pipelines.classical.enrich_features import _asn_bucket
from pipelines.classical.typosquat import brand_similarity

# Risk score starting weights [exact] (PLAN 7.2).
W_CONFIDENCE = 25
W_USERS = 20
W_RECENCY = 15
W_SIMILARITY = 15
W_CREDENTIAL = 10
W_PRIVILEGED = 10
W_REPEAT = 5

GOLD_COLS = [
    "finding_id", "domain", "risk_score",
    "max_source_confidence", "distinct_users_hit", "days_since_first_seen",
    "brand_similarity_score", "credential_entry_flag", "privileged_user_flag",
    "repeat_access_flag", "intel_sources", "report_only",
]


def _distinct_users(dns: pd.DataFrame, proxy: pd.DataFrame, domain: str) -> set[str]:
    users = set()
    users.update(dns.loc[dns["query_domain"] == domain, "employee_id"])
    users.update(proxy.loc[proxy["domain"] == domain, "employee_id"])
    return {u for u in users if pd.notna(u)}


def _credential_entry(proxy: pd.DataFrame, domain: str) -> bool:
    """Any POST to a kit path on the domain (a credential submission)."""
    posts = proxy[(proxy["domain"] == domain) & (proxy["method"] == "POST")]
    return len(posts) > 0


def _repeat_access(dns: pd.DataFrame, proxy: pd.DataFrame, domain: str) -> bool:
    """Any single user with >= REPEAT_ACCESS_THRESHOLD hits on the domain."""
    hits = pd.concat([
        dns.loc[dns["query_domain"] == domain, "employee_id"],
        proxy.loc[proxy["domain"] == domain, "employee_id"],
    ])
    if hits.empty:
        return False
    return int(hits.value_counts().max()) >= config.REPEAT_ACCESS_THRESHOLD


def _privileged_hit(dns, proxy, employees_priv: set[str], domain: str) -> bool:
    return len(_distinct_users(dns, proxy, domain) & employees_priv) > 0


def compute_findings(
    candidate_domains: pd.DataFrame,
    dns: pd.DataFrame,
    proxy: pd.DataFrame,
    employees: pd.DataFrame,
    reference_ts: pd.Timestamp,
) -> pd.DataFrame:
    """Score each candidate domain into a gold finding.

    candidate_domains: frame with columns domain, max_source_confidence,
        first_seen (timestamp), intel_sources (list[str]), report_only (bool).
    """
    priv_ids = set(employees.loc[employees["is_privileged"], "employee_id"])
    rows = []

    for _, cand in candidate_domains.iterrows():
        domain = cand["domain"]
        users = _distinct_users(dns, proxy, domain)
        n_users = len(users)
        conf = float(cand.get("max_source_confidence", 0) or 0)
        first_seen = cand.get("first_seen")
        if pd.notna(first_seen):
            days_since = max(0.0, (reference_ts - pd.Timestamp(first_seen)).total_seconds() / 86400.0)
        else:
            days_since = 7.0
        sim, _ = brand_similarity(domain)
        cred = _credential_entry(proxy, domain)
        priv = _privileged_hit(dns, proxy, priv_ids, domain)
        repeat = _repeat_access(dns, proxy, domain)

        score = (
            W_CONFIDENCE * (conf / 100.0)
            + W_USERS * min(n_users / 10.0, 1.0)
            + W_RECENCY * math.exp(-days_since / 7.0)
            + W_SIMILARITY * (sim / 100.0)
            + W_CREDENTIAL * (1 if cred else 0)
            + W_PRIVILEGED * (1 if priv else 0)
            + W_REPEAT * (1 if repeat else 0)
        )

        rows.append({
            "finding_id": f"F-{domain}",
            "domain": domain,
            "risk_score": round(score, 2),
            "max_source_confidence": conf,
            "distinct_users_hit": n_users,
            "days_since_first_seen": round(days_since, 2),
            "brand_similarity_score": round(sim, 1),
            "credential_entry_flag": int(cred),
            "privileged_user_flag": int(priv),
            "repeat_access_flag": int(repeat),
            "intel_sources": cand.get("intel_sources", []),
            "report_only": bool(cand.get("report_only", False)),
        })

    gold = pd.DataFrame(rows, columns=GOLD_COLS)
    return gold.sort_values("risk_score", ascending=False).reset_index(drop=True)


def report_only_metric(gold: pd.DataFrame, dns: pd.DataFrame) -> dict:
    """AP3 metric (PLAN 5.4): report-only findings = domains + distinct users."""
    ro = gold[gold["report_only"]]
    users = set()
    for d in ro["domain"]:
        users.update(dns.loc[dns["query_domain"] == d, "employee_id"])
    return {"report_only_domains": len(ro), "report_only_users": len({u for u in users if pd.notna(u)})}
