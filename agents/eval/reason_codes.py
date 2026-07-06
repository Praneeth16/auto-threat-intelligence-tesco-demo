"""Feedback taxonomy and routing (PLAN 10.1).

Both lanes produce feedback: the human lane (reason-coded verdict from the
Approval Queue) and the auto lane (auto-resolutions scored against ground truth
after the fact). The reason code routes the feedback to the right destination.
Only reason-coded, confirmed decisions enter case memory; ambiguous ones stay
eval-only. Humans mislabel too, so this is stated on stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Reason codes [exact] (PLAN 6.1).
REASON_CODES = [
    "wrong_classification", "insufficient_evidence", "wrong_action", "policy_exception",
]


class Destination(str, Enum):
    EVAL_DATASET = "eval_dataset"
    CASE_MEMORY = "case_memory"
    POLICY_REVIEW = "policy_review"
    ALLOWLIST = "allowlist"
    POLICY_STORE = "policy_store"


# Routing table (PLAN 10.1). A reason code can fan out to several destinations.
ROUTING: dict[str, list[Destination]] = {
    # Agent got the verdict wrong: teach it (eval) and record the case.
    "wrong_classification": [Destination.EVAL_DATASET, Destination.CASE_MEMORY],
    # Tighten tool use / prompt.
    "insufficient_evidence": [Destination.EVAL_DATASET],
    # Wrong action: eval plus a policy review.
    "wrong_action": [Destination.EVAL_DATASET, Destination.POLICY_REVIEW],
    # The agent reasoned correctly on the info it had; this is a policy fact,
    # NOT an agent-memory lesson. Goes to the allowlist and policy_store only.
    "policy_exception": [Destination.ALLOWLIST, Destination.POLICY_STORE],
}


@dataclass
class FeedbackRouting:
    reason_code: str
    destinations: list[Destination]
    enters_case_memory: bool


def route_feedback(reason_code: str) -> FeedbackRouting:
    """Return where a reason-coded verdict should be written.

    policy_exception deliberately does NOT enter agent case memory: the agent
    was right on the evidence it had, so the fix is a policy allowlist entry,
    not a lesson that would teach it to under-escalate similar domains.
    """
    if reason_code not in ROUTING:
        raise ValueError(f"unknown reason code: {reason_code}")
    dests = ROUTING[reason_code]
    return FeedbackRouting(
        reason_code=reason_code,
        destinations=dests,
        enters_case_memory=Destination.CASE_MEMORY in dests,
    )
