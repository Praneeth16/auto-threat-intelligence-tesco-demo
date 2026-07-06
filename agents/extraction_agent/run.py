"""Extraction agent runner (PLAN 8.2).

Agent Bricks Information Extraction agent over the Section 5.8 schema. Called by
pipelines/stream/extract_reports.py. Invoked as an explicit FMAPI serving
endpoint call (not ai_query), matching the Stage 4 decision, with structured
JSON output and defensive parsing.

Returns one row per report with the extracted entities so the pipeline can
write silver_report_entities and score AI recall against gt_report_entities.
"""

from __future__ import annotations

import json

import pandas as pd

# Extraction schema (PLAN 5.8).
SCHEMA_KEYS = ["actors", "iocs", "ttps", "targeted_brands", "phishing_kits",
               "confidence", "summary", "recommended_detections"]

_PROMPT = (
    "Extract threat intelligence from the report as strict JSON with keys: "
    "actors (list of strings), iocs (list of {value,type}), ttps (list of "
    "MITRE IDs), targeted_brands (list), phishing_kits (list), confidence "
    "(low|medium|high), summary (string), recommended_detections (list). "
    "Include only entities present in the text. Do not invent brand relevance. "
    "Return JSON only, no prose.\n\nReport:\n"
)


def _empty_extraction() -> dict:
    return {"actors": [], "iocs": [], "ttps": [], "targeted_brands": [],
            "phishing_kits": [], "confidence": "low", "summary": "",
            "recommended_detections": []}


def _parse(raw: str) -> dict:
    """Parse model JSON defensively; return an empty extraction on failure."""
    try:
        # Strip code fences if the model wrapped the JSON.
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1].lstrip("json").strip()
        data = json.loads(text)
        out = _empty_extraction()
        for k in SCHEMA_KEYS:
            if k in data:
                out[k] = data[k]
        return out
    except (ValueError, IndexError, TypeError):
        return _empty_extraction()


def extract_one(body: str, endpoint: str, client) -> dict:
    """Call the extraction endpoint on one report body; parse to schema."""
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

    messages = [ChatMessage(role=ChatMessageRole.USER, content=_PROMPT + body)]
    try:
        resp = client.serving_endpoints.query(name=endpoint, messages=messages, max_tokens=800)
    except Exception:
        return _empty_extraction()
    content = resp.choices[0].message.content if resp.choices else ""
    return _parse(content or "")


def run_extraction(reports: pd.DataFrame, endpoint: str | None = None, client=None) -> list[dict]:
    """Extract every report. Requires a live client; raises if absent so the
    caller falls back to ground truth for the reference build."""
    if client is None:
        from databricks.sdk import WorkspaceClient

        from pipelines.stream.enrichment_llm import resolve_endpoint

        client = WorkspaceClient()
        endpoint = endpoint or resolve_endpoint()
    rows = []
    for _, r in reports.iterrows():
        extraction = extract_one(r["body"], endpoint, client)
        rows.append({"report_id": r["report_id"],
                     "extraction_json": json.dumps(extraction)})
    return rows
