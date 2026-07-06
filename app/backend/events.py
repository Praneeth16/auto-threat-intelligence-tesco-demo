"""SSE event types (PLAN 9.3) [exact names].

One stream multiplexes these typed events. Two deliberate simplifications from
the plan: no per-row event.ingested type (aggregate counts ride on replay.tick),
and agent.step carries only the tool name (full trace via the traces endpoint).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Exact event type names (PLAN 9.3).
REPLAY_TICK = "replay.tick"
FINDING_UPDATED = "finding.updated"
AGENT_STARTED = "agent.started"
AGENT_STEP = "agent.step"
AGENT_COMPLETED = "agent.completed"
DECISION_ROUTED = "decision.routed"
QUEUE_UPDATED = "queue.updated"
METRICS_UPDATED = "metrics.updated"

EVENT_TYPES = {
    REPLAY_TICK, FINDING_UPDATED, AGENT_STARTED, AGENT_STEP,
    AGENT_COMPLETED, DECISION_ROUTED, QUEUE_UPDATED, METRICS_UPDATED,
}


@dataclass
class SSEEvent:
    """A typed SSE event with a monotonic id for Last-Event-ID reconnect."""

    event: str
    data: dict[str, Any]
    id: int = 0

    def format(self) -> dict[str, str]:
        """Return the sse-starlette payload dict (event, data, id)."""
        import json

        return {"event": self.event, "data": json.dumps(self.data), "id": str(self.id)}


# Typed constructors so payload shapes match PLAN 9.3 exactly.
def replay_tick(sim_clock, speed, running, dns=0, proxy=0, email=0, auth=0) -> dict:
    return {"sim_clock": str(sim_clock), "speed": speed, "running": running,
            "ingested_since_last": {"dns": dns, "proxy": proxy, "email": email, "auth": auth}}


def finding_updated(finding_id, domain, risk_score, components, status) -> dict:
    return {"finding_id": finding_id, "domain": domain, "risk_score": risk_score,
            "components": components, "status": status}


def agent_started(finding_id, agent_run_id) -> dict:
    return {"finding_id": finding_id, "agent_run_id": agent_run_id}


def agent_step(agent_run_id, tool) -> dict:
    return {"agent_run_id": agent_run_id, "tool": tool}


def agent_completed(agent_run_id, finding_id, brief_excerpt, recommended_action,
                    tier, confidence, groundedness) -> dict:
    return {"agent_run_id": agent_run_id, "finding_id": finding_id,
            "brief_excerpt": brief_excerpt, "recommended_action": recommended_action,
            "tier": tier, "confidence": confidence, "groundedness": groundedness}


def decision_routed(decision_id, finding_id, route, tier, action) -> dict:
    return {"decision_id": decision_id, "finding_id": finding_id,
            "route": route, "tier": tier, "action": action}


def queue_updated(queue_id, status) -> dict:
    return {"queue_id": queue_id, "status": status}


def metrics_updated(auto_resolved, auto_executed, queued, agreement_rate,
                    escalation_rate, tokens) -> dict:
    return {"auto_resolved": auto_resolved, "auto_executed": auto_executed,
            "queued": queued, "agreement_rate": agreement_rate,
            "escalation_rate": escalation_rate, "tokens": tokens}
