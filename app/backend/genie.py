"""Genie Q&A proxy for the Executive Overview tab (PLAN 002 U4).

Answers natural-language questions over the SOC datasets. In-workspace, when
SOC_GENIE_SPACE_ID is set, it calls the Databricks Genie Conversation API for
that space. Locally and in the demo (no space id, or any live failure), it
returns a deterministic scripted answer over the storyline dataset — the same
offline-safe principle the replay simulator uses, so the demo never depends on
a live Genie space or the SSO-walled network.

The response shape is identical on both paths: {answer, source, sql?, rows?}.
"""

from __future__ import annotations

import os

# Scripted answers over the FreshCart PhishOps storyline (matches datagen ground
# truth). Keyed by substrings we look for in a lowercased question. First match
# wins, so order the more specific keys first.
_SCRIPTED = [
    (("top campaign", "biggest campaign", "which campaign", "campaign"),
     "The top campaign is FreshCart PhishOps: five lookalike domains impersonating "
     "Tesco Clubcard, TescoBank, rewards, supplier billing, and parcel tracking. "
     "The hero domain tesco-clubcard-support[.]com scored 82 and drew internal contact."),
    (("how many anomal", "anomaly count", "anomalies"),
     "5 anomalies surfaced this run — the five FreshCart PhishOps findings that "
     "crossed the triage threshold out of 18,120 telemetry events."),
    (("hero", "highest", "top finding", "top risk", "worst"),
     "The hero finding is tesco-clubcard-support[.]com at risk score 82 (critical): "
     "90 brand similarity, 17 affected users, credential entry seen, privileged account."),
    (("auto-resolved", "auto resolved", "auto-close", "auto lane", "how many auto"),
     "The auto lane cleared the commodity noise: ~55 prefilter closes and ~50 tier-0 "
     "auto-executions, leaving only the hero tier-2 action for human approval."),
    (("agreement", "agree"),
     "Agent-human agreement is 90% on this run — the one queued tier-2 action matched "
     "the reviewer's verdict."),
    (("escalation", "escalate"),
     "Escalation rate is ~20%: one of the five anomalies escalated to the human "
     "approval gate; the rest auto-resolved."),
    (("token", "cost"),
     "The run spent ~14,400 gateway tokens across triage and the hero agent's "
     "six-tool investigation loop."),
    (("who is affected", "affected user", "priya"),
     "Priya Nair is the affected user on the hero domain: 17 distinct users touched "
     "the phishing infrastructure, with 3 credential submissions."),
]

_DEFAULT = (
    "This Genie space answers questions over the FreshCart PhishOps SOC datasets — "
    "try asking about the top campaign, how many anomalies surfaced, the hero finding, "
    "or the auto-resolved volume."
)


def _scripted_answer(question: str) -> dict:
    q = (question or "").lower()
    for keys, answer in _SCRIPTED:
        if any(k in q for k in keys):
            return {"answer": answer, "source": "scripted"}
    return {"answer": _DEFAULT, "source": "scripted"}


def _live_answer(question: str, space_id: str) -> dict:
    """Call the Databricks Genie Conversation API for the configured space.

    Any failure raises; the caller degrades to the scripted answer so the demo
    is never left with a 500 or a blank panel.
    """
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    genie = w.genie
    # start_conversation_and_wait blocks until the message completes; it returns
    # the final GenieMessage with any text attachment / query result.
    msg = genie.start_conversation_and_wait(space_id=space_id, content=question)

    answer_parts: list[str] = []
    sql: str | None = None
    rows: list | None = None
    for att in (getattr(msg, "attachments", None) or []):
        text = getattr(att, "text", None)
        if text and getattr(text, "content", None):
            answer_parts.append(text.content)
        query = getattr(att, "query", None)
        if query is not None:
            sql = getattr(query, "query", None) or sql
            desc = getattr(query, "description", None)
            if desc:
                answer_parts.append(desc)
    answer = "\n\n".join(answer_parts) or getattr(msg, "content", None) or _DEFAULT
    out = {"answer": answer, "source": "genie"}
    if sql:
        out["sql"] = sql
    if rows:
        out["rows"] = rows
    return out


async def ask(question: str) -> dict:
    """Answer a question over the SOC data. Live Genie when configured, scripted
    fallback otherwise or on any live failure. Always returns {answer, source}."""
    space_id = os.environ.get("SOC_GENIE_SPACE_ID")
    if space_id:
        try:
            return _live_answer(question, space_id)
        except Exception:
            # Degrade to the deterministic answer rather than surface a 500.
            fallback = _scripted_answer(question)
            fallback["source"] = "scripted_fallback"
            return fallback
    return _scripted_answer(question)
