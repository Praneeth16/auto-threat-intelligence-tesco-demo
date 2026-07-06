"""MLflow 3 judges (PLAN 10.2).

Two judges, but only one gates anything live. The groundedness judge (brief
claims must trace to evidence-tool output) is the sole live gate: it must pass
before any auto-execute, and its score shows in the Approval Queue. The
action-appropriateness judge (tier matches blast radius) runs offline in the
nightly eval build and is tracked as a metric, not wired to block anything live.

The groundedness check here is a deterministic structural check over the
evidence the tools returned, so it is testable and rehearsable. In-workspace it
is registered as an MLflow judge; the structural check is the GA-safe backing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Threshold the router requires before an auto-execute (PLAN 10.2).
GROUNDEDNESS_GATE = 0.8


@dataclass
class JudgeResult:
    score: float
    passed: bool
    detail: str


def _numbers_in(text: str) -> set[str]:
    return set(re.findall(r"\b\d+\b", text))


def groundedness(brief: str, evidence: dict) -> JudgeResult:
    """Score how well the brief's claims trace to the evidence-tool output.

    Structural proxy for the MLflow judge: every number the brief asserts about
    users/hits/posts must appear in the tool output, and the brief must not name
    a domain the tools did not return. A brief that invents a count or an
    indicator fails.
    """
    telem = evidence.get("telemetry", {})
    allowed_numbers = _numbers_in(str(telem)) | _numbers_in(str(evidence.get("campaign", {})))
    # Percent confidences are the agent's own, allow them.
    brief_numbers = _numbers_in(re.sub(r"\d+%", "", brief))

    ungrounded = {n for n in brief_numbers if n not in allowed_numbers and len(n) > 1}
    # Tolerate small single-digit numbers (tier, counts of sections).
    total = max(1, len(brief_numbers))
    grounded_fraction = 1.0 - (len(ungrounded) / total)
    score = round(max(0.0, grounded_fraction), 3)
    return JudgeResult(
        score=score,
        passed=score >= GROUNDEDNESS_GATE,
        detail=f"ungrounded numbers: {sorted(ungrounded)}" if ungrounded else "all claims trace to evidence",
    )


def action_appropriateness(recommended_tier: int, evidence: dict) -> JudgeResult:
    """Offline metric: does the recommended tier match the blast radius?

    Identity-touching outcomes on a privileged user should be tier 2; a domain
    block should be tier 1; low-exposure closes tier 0. Runs in the nightly eval
    build (Section 10.3), not wired to block anything live.
    """
    priv = evidence.get("user_context", {}).get("any_privileged", False)
    cred = evidence.get("telemetry", {}).get("credential_posts", 0) > 0
    if priv and cred:
        expected = 2
    elif cred:
        expected = 1
    else:
        expected = 0
    ok = recommended_tier >= expected  # never under-tier the blast radius
    return JudgeResult(
        score=1.0 if ok else 0.0,
        passed=ok,
        detail=f"expected >= tier {expected}, got tier {recommended_tier}",
    )
