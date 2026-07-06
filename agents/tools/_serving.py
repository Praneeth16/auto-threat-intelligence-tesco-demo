"""Thin FMAPI serving-endpoint call for agent briefs (governed via AI Gateway).

Explicit serving-endpoint call, not ai_query, matching the Stage 4 enrichment
decision. Used by the triage agent to write the grounded brief when a live
model client is available.
"""

from __future__ import annotations


def chat_brief(endpoint, system_prompt, facts, action, tier, confidence, client) -> str:
    """Ask the model to write the brief from the evidence facts only."""
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

    user = (
        "Write the triage brief for this finding using ONLY these evidence "
        "facts. Recommend the action given, with its tier and confidence.\n\n"
        f"Evidence facts:\n{facts}\n\n"
        f"Recommended action: {action} (tier {tier}); confidence {confidence:.0%}."
    )
    messages = [
        ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
        ChatMessage(role=ChatMessageRole.USER, content=user),
    ]
    try:
        resp = client.serving_endpoints.query(
            name=endpoint, messages=messages, temperature=0.0, max_tokens=400
        )
    except Exception as exc:
        if "temperature" not in str(exc).lower():
            raise
        resp = client.serving_endpoints.query(
            name=endpoint, messages=messages, max_tokens=400
        )
    content = resp.choices[0].message.content if resp.choices else ""
    return (content or "").strip()
