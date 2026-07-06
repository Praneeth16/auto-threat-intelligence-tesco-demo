"""Policy router (PLAN 8.4). The GA-safe tier-2 human gate.

Routes on confidence AND blast radius, not confidence alone. Composite
confidence is deterministic-dominant: exact IOC match, risk score, and brand
similarity carry the weight, with the model's self-reported confidence a minor
input. The groundedness judge (Stage 8) must pass before any auto-execute; this
router assumes that gate and enforces the tier matrix.

Pure Python so the routing is fully testable and rehearsable. Reads the seeded
policy_store (Stage 3) at runtime; the tier matrix here mirrors POLICY_V1.

Tier matrix:
  Tier 0: close-as-benign, merge-duplicate, add-to-watchlist, enrich
          -> auto if composite >= threshold (0.85)
  Tier 1: block-domain-at-proxy
          -> auto only if exact high-confidence IOC match; notify + reversible
  Tier 2: password-reset, account-disable (identity)
          -> never auto; always human queue, any confidence

Allowlist check precedes tiering: an allowlisted domain closes as benign citing
its entry (this is how the clubcard-autumn sibling auto-closes after the summer
exception is recorded).
"""

from __future__ import annotations

from dataclasses import dataclass

# Action -> tier, mirroring the seeded policy_store (PLAN 8.4).
ACTION_TIER = {
    "close-as-benign": 0,
    "merge-duplicate": 0,
    "add-to-watchlist": 0,
    "enrich": 0,
    "block-domain-at-proxy": 1,
    "password-reset": 2,
    "account-disable": 2,
}

TIER0_THRESHOLD = 0.85

# Composite confidence weights: deterministic components dominate.
W_EXACT_IOC = 0.40
W_RISK = 0.30
W_SIMILARITY = 0.20
W_MODEL = 0.10  # the agent's self-reported confidence is a minor input


@dataclass
class RouteDecision:
    route: str  # auto_execute | human_queue
    action: str
    action_tier: int
    composite_confidence: float
    reversible: bool
    reason: str
    allowlisted: bool = False


def composite_confidence(
    exact_ioc_match: bool,
    risk_score: float,
    brand_similarity: float,
    model_confidence: float,
) -> float:
    """Blend deterministic signals (dominant) with the model's self-report.

    risk_score is 0-100, brand_similarity 0-100, model_confidence 0-1.
    Returns a 0-1 composite.
    """
    return round(
        W_EXACT_IOC * (1.0 if exact_ioc_match else 0.0)
        + W_RISK * (risk_score / 100.0)
        + W_SIMILARITY * (brand_similarity / 100.0)
        + W_MODEL * max(0.0, min(1.0, model_confidence)),
        4,
    )


def route(
    action: str,
    *,
    domain: str,
    exact_ioc_match: bool,
    risk_score: float,
    brand_similarity: float,
    model_confidence: float,
    groundedness_passed: bool,
    allowlist: set[str] | None = None,
) -> RouteDecision:
    """Route a recommended action through the tier matrix.

    allowlist: set of allowlisted domains; an allowlisted domain closes as
    benign citing its entry before tiering.
    """
    allowlist = allowlist or set()
    comp = composite_confidence(exact_ioc_match, risk_score, brand_similarity, model_confidence)

    # Allowlist precedes tiering.
    if domain in allowlist:
        return RouteDecision(
            route="auto_execute",
            action="close-as-benign",
            action_tier=0,
            composite_confidence=comp,
            reversible=True,
            reason=f"allowlisted domain {domain}; closed as benign citing allowlist entry",
            allowlisted=True,
        )

    tier = ACTION_TIER.get(action)
    if tier is None:
        # Unknown action is never auto-executed.
        return RouteDecision("human_queue", action, -1, comp, True,
                             f"unknown action {action}; routed to human queue")

    # Tier 2: identity actions never auto, any confidence.
    if tier == 2:
        return RouteDecision("human_queue", action, 2, comp, False,
                             "tier-2 identity action; always human queue")

    # Tier 1: block-domain-at-proxy, auto only on exact high-confidence IOC match.
    if tier == 1:
        if exact_ioc_match and groundedness_passed:
            return RouteDecision("auto_execute", action, 1, comp, True,
                                 "tier-1 block on exact high-confidence IOC match; notify + reversible")
        return RouteDecision("human_queue", action, 1, comp, True,
                             "tier-1 block without exact IOC match or failed groundedness; queued")

    # Tier 0: auto if composite >= threshold and groundedness passed.
    if comp >= TIER0_THRESHOLD and groundedness_passed:
        return RouteDecision("auto_execute", action, 0, comp, True,
                             f"tier-0 auto: composite {comp} >= {TIER0_THRESHOLD}")
    return RouteDecision("human_queue", action, 0, comp, True,
                         f"tier-0 below threshold ({comp} < {TIER0_THRESHOLD}); queued")
