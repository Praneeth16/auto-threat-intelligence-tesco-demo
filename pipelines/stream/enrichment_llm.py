"""LLM enrichment via an explicit Model Serving endpoint call.

Not ai_query. The enrichment sentence is produced by calling a governed Model
Serving endpoint (FMAPI, routed through AI Gateway) with the serving-endpoints
query API, so the model call is explicit, governed, and swappable, rather than
hidden inside a SQL function. The heavy agentic reasoning is the Stage 5 Agent
Bricks triage agent; this is only the per-domain feature-grounded classification
column on gold_findings.

Deterministic-friendly: temperature 0, a short max_tokens, and the prompt is
constrained to the structured features so the model does not invent facts.
"""

from __future__ import annotations

import pandas as pd

# Ordered endpoint preference; resolve_endpoint picks the first present. An
# instruct model leads: it returns chat content cleanly and accepts the params
# below, unlike gemini-flash (empty content) and the newest reasoning models
# (reject temperature).
_PREFERRED = [
    "databricks-meta-llama-3-3-70b-instruct",
    "databricks-claude-opus-4-8",
    "databricks-gpt-5-5",
    "databricks-gemini-3-5-flash",
]

_SYSTEM = (
    "You are a SOC triage assistant. Classify a suspicious domain in one short "
    "sentence using only the structured features provided. Do not invent facts "
    "or indicators not in the features. No preamble."
)


def resolve_endpoint(preferred: str | None = None) -> str:
    """Return the first available serving endpoint from the preference list."""
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    available = {e.name for e in w.serving_endpoints.list()}
    order = ([preferred] if preferred else []) + _PREFERRED
    for name in order:
        if name and name in available:
            return name
    raise RuntimeError(f"no FMAPI serving endpoint available from {order}")


def _feature_line(row: pd.Series) -> str:
    return (
        f"Domain: {row['domain']} | "
        f"brand_similarity: {row['brand_similarity_score']} | "
        f"distinct_users: {row['distinct_users_hit']} | "
        f"credential_entry: {row['credential_entry_flag']} | "
        f"privileged_user: {row['privileged_user_flag']} | "
        f"source_confidence: {row['max_source_confidence']} | "
        f"days_since_first_seen: {row['days_since_first_seen']}"
    )


def classify_domain(endpoint: str, features: str, client=None) -> str:
    """Call the serving endpoint once; return the one-sentence classification.

    Sends temperature=0 for determinism, but the newest reasoning models reject
    that param, so a BadRequest triggers one retry without it.
    """
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

    w = client or WorkspaceClient()
    messages = [
        ChatMessage(role=ChatMessageRole.SYSTEM, content=_SYSTEM),
        ChatMessage(role=ChatMessageRole.USER, content=features),
    ]
    try:
        resp = w.serving_endpoints.query(
            name=endpoint, messages=messages, temperature=0.0, max_tokens=120
        )
    except Exception as exc:
        if "temperature" not in str(exc).lower():
            raise
        resp = w.serving_endpoints.query(
            name=endpoint, messages=messages, max_tokens=120
        )
    content = resp.choices[0].message.content if resp.choices else ""
    return (content or "").strip()


def add_ai_classification(gold: pd.DataFrame, endpoint: str | None = None) -> pd.DataFrame:
    """Add an ai_classification column by calling the serving endpoint per row.

    Governed: every call goes through the resolved FMAPI serving endpoint (AI
    Gateway routes apply). Falls back to a feature-derived note if a call fails
    so the pipeline never blocks on a transient model error.
    """
    ep = resolve_endpoint(endpoint)
    out = gold.copy()
    classifications = []
    for _, row in out.iterrows():
        try:
            classifications.append(classify_domain(ep, _feature_line(row)))
        except Exception as exc:  # transient model/gateway error; degrade gracefully
            classifications.append(f"(enrichment unavailable: {type(exc).__name__})")
    out["ai_classification"] = classifications
    out["ai_endpoint"] = ep
    return out
