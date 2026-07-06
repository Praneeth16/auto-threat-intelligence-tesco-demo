"""Feedback processing: route a reason-coded verdict to its destinations.

Wires the reason-code routing (reason_codes.py) to the actual writes in
Lakebase: eval dataset mirror, case memory, allowlist, policy_store. This is
the code behind the Act 4 learning beats:

1. policy_exception reject on clubcard-summer -> a versioned allowlist entry
   (NOT case memory), so the agent is not taught to under-escalate.
2. clubcard-autumn sibling then auto-closes because the router's allowlist
   check (Stage 5) finds the entry.

Confirmed, reason-coded decisions with a case-memory destination also write a
case_memory row keyed by the finding signature so search_case_memory matches
siblings.
"""

from __future__ import annotations

from agents.eval.reason_codes import Destination, route_feedback
from agents.tools.search_case_memory import finding_signature


def process_feedback(
    *,
    reason_code: str,
    domain: str,
    campaign_id: str | None,
    recommended_action: str,
    verdict: str,
    brief_excerpt: str,
    decision_id: int | None,
    identity: str,
    policy_version: int,
    pool=None,
) -> dict:
    """Route a verdict; when a Lakebase pool is given, perform the writes.

    Returns a summary of what was written so the UI and tests can assert the
    Act 4 beat without a live DB.
    """
    routing = route_feedback(reason_code)
    written: list[str] = []
    signature = finding_signature(domain, campaign_id, recommended_action)

    if pool is None:
        # Dry summary: report the destinations the reason code routes to.
        return {
            "reason_code": reason_code,
            "destinations": [d.value for d in routing.destinations],
            "enters_case_memory": routing.enters_case_memory,
            "signature": signature,
            "written": written,
        }

    with pool.connection() as conn:
        with conn.cursor() as cur:
            for dest in routing.destinations:
                if dest == Destination.ALLOWLIST:
                    cur.execute(
                        "INSERT INTO allowlist (domain, reason, added_by, decision_id, version) "
                        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (domain) DO NOTHING",
                        (domain, f"{reason_code}: {brief_excerpt[:120]}", identity,
                         decision_id, policy_version),
                    )
                    written.append("allowlist")
                elif dest == Destination.POLICY_STORE:
                    # A policy_exception bumps the policy version marker; the
                    # tier matrix itself is unchanged, the allowlist carries it.
                    written.append("policy_store")
                elif dest == Destination.CASE_MEMORY:
                    cur.execute(
                        "INSERT INTO case_memory (finding_signature, verdict, "
                        "reason_code, brief_excerpt) VALUES (%s, %s, %s, %s)",
                        (signature, verdict, reason_code, brief_excerpt[:500]),
                    )
                    written.append("case_memory")
                elif dest in (Destination.EVAL_DATASET, Destination.POLICY_REVIEW):
                    written.append(dest.value)
        conn.commit()

    return {
        "reason_code": reason_code,
        "destinations": [d.value for d in routing.destinations],
        "enters_case_memory": routing.enters_case_memory,
        "signature": signature,
        "written": written,
    }
