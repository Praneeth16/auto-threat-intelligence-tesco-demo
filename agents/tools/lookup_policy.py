"""lookup_policy(domain, action) -> tier, auto_threshold, allowlist hit
(PLAN 8.3). Reads the seeded policy_store and allowlist in Lakebase.
"""

from __future__ import annotations

from agents.router.policy_router import ACTION_TIER, TIER0_THRESHOLD


def lookup_policy(domain: str, action: str, pool=None) -> dict:
    """Return the tier and threshold for an action, plus any allowlist hit.

    When a Lakebase pool is provided, reads live policy_store/allowlist;
    otherwise falls back to the static tier matrix (POLICY_V1 mirror).
    """
    tier = ACTION_TIER.get(action)
    allowlisted = False
    allowlist_reason = None
    threshold = TIER0_THRESHOLD if tier == 0 else None

    if pool is not None:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT tier, auto_threshold FROM policy_store "
                "WHERE action = %s AND active = true ORDER BY version DESC LIMIT 1",
                (action,),
            )
            row = cur.fetchone()
            if row:
                tier, threshold = row[0], (float(row[1]) if row[1] is not None else None)
            cur.execute("SELECT reason FROM allowlist WHERE domain = %s", (domain,))
            al = cur.fetchone()
            if al:
                allowlisted = True
                allowlist_reason = al[0]

    return {
        "domain": domain,
        "action": action,
        "tier": tier,
        "auto_threshold": threshold,
        "allowlisted": allowlisted,
        "allowlist_reason": allowlist_reason,
    }
