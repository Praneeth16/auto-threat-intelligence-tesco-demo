"""Seed policy_store version 1 with the tier matrix (PLAN 8.4) and an empty
allowlist. Idempotent: seeding twice does not duplicate version-1 rows.

The tier matrix is defined as data (POLICY_V1) so it can be unit-tested without
a live Lakebase, and applied by seed() when a database is available.
"""

from __future__ import annotations

from dataclasses import dataclass

POLICY_VERSION = 1


@dataclass(frozen=True)
class PolicyRow:
    action: str
    tier: int
    auto_threshold: float | None
    requires_exact_ioc: bool
    notify: bool
    reversible: bool


# Tier matrix seeded in policy_store [exact] (PLAN 8.4).
#   Tier 0: auto if composite >= threshold.
#   Tier 1: auto only if exact high-confidence IOC match; notify + reversible.
#   Tier 2: never auto; always human queue, any confidence.
POLICY_V1: list[PolicyRow] = [
    # Tier 0
    PolicyRow("close-as-benign", 0, 0.85, False, False, True),
    PolicyRow("merge-duplicate", 0, 0.85, False, False, True),
    PolicyRow("add-to-watchlist", 0, 0.85, False, False, True),
    PolicyRow("enrich", 0, 0.85, False, False, True),
    # Tier 1
    PolicyRow("block-domain-at-proxy", 1, None, True, True, True),
    # Tier 2 (identity actions; never auto)
    PolicyRow("password-reset", 2, None, False, True, False),
    PolicyRow("account-disable", 2, None, False, True, False),
]


def seed(pool=None) -> None:
    """Insert version-1 policy rows if absent. Empty allowlist stays empty."""
    if pool is None:
        from app.db.connection import make_pool

        pool = make_pool(min_size=1, max_size=2)
        _owned = True
    else:
        _owned = False

    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM policy_store WHERE version = %s",
                    (POLICY_VERSION,),
                )
                (existing,) = cur.fetchone()
                if existing:
                    print(f"policy_store v{POLICY_VERSION} already seeded ({existing} rows)")
                    return
                for p in POLICY_V1:
                    cur.execute(
                        """
                        INSERT INTO policy_store
                            (version, action, tier, auto_threshold,
                             requires_exact_ioc, notify, reversible, active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, true)
                        """,
                        (POLICY_VERSION, p.action, p.tier, p.auto_threshold,
                         p.requires_exact_ioc, p.notify, p.reversible),
                    )
            conn.commit()
        print(f"seeded policy_store v{POLICY_VERSION}: {len(POLICY_V1)} rows")
    finally:
        if _owned:
            pool.close()


if __name__ == "__main__":
    seed()
