"""Unity AI Gateway configuration for the SOC demo (PLAN 8.5).

All model traffic (enrichment serving-endpoint calls and agent turns) egresses
through AI Gateway: guardrails, per-workload budgets, usage tracking, provider
fallback. Model choice is a live demo point: FMAPI exposes multiple providers
under one governance surface, so the enrichment model can be flipped live to
show the cost/quality tradeoff.

This module documents the intended routes and budgets as data; the instructor
applies them from the AI Gateway UI (PLAN Section 15). The Lakebase policy
router is the primary, GA-safe tier-2 gate; managed Omnigent (beta) is a
forward-slide direction only.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GatewayRoute:
    name: str
    served_endpoints: tuple[str, ...]  # primary first, then fallbacks
    monthly_budget_usd: int
    guardrails: tuple[str, ...] = field(default_factory=tuple)


# Two workloads share the gateway: pipeline enrichment and agent turns.
ROUTES = [
    GatewayRoute(
        name="soc-enrichment",
        served_endpoints=(
            "databricks-meta-llama-3-3-70b-instruct",
            "databricks-claude-opus-4-8",
            "databricks-gpt-5-5",
        ),
        monthly_budget_usd=50,
        guardrails=("pii", "toxicity"),
    ),
    GatewayRoute(
        name="soc-agent",
        served_endpoints=(
            "databricks-claude-opus-4-8",
            "databricks-meta-llama-3-3-70b-instruct",
        ),
        monthly_budget_usd=100,
        guardrails=("pii",),
    ),
]
