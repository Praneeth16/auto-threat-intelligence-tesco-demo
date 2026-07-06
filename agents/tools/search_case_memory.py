"""search_case_memory(finding_signature) -> prior adjudicated cases (PLAN 8.3).

Reads the case_memory_v view in Lakebase. The finding_signature is a stable
key (campaign + action shape) so the clubcard-autumn sibling matches the
recorded clubcard-summer exception.
"""

from __future__ import annotations


def finding_signature(domain: str, campaign_id: str | None, recommended_action: str) -> str:
    """Build the stable signature used to match prior cases.

    Uses the campaign and action, not the exact domain, so a sibling domain in
    the same family matches a recorded precedent.
    """
    return f"{campaign_id or 'none'}::{recommended_action}"


def search_case_memory(signature: str, pool=None, limit: int = 5) -> dict:
    """Return prior adjudicated cases matching a finding signature."""
    if pool is None:
        return {"signature": signature, "matches": []}
    matches = []
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT case_id, verdict, reason_code, brief_excerpt, created_at "
            "FROM case_memory_v WHERE finding_signature = %s "
            "ORDER BY created_at DESC LIMIT %s",
            (signature, limit),
        )
        for row in cur.fetchall():
            matches.append({
                "case_id": row[0],
                "verdict": row[1],
                "reason_code": row[2],
                "brief_excerpt": row[3],
                "created_at": str(row[4]),
            })
    return {"signature": signature, "matches": matches}
