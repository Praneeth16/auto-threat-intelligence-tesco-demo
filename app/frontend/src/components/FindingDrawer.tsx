// Finding detail drawer: slides in from the right when a Triage Board row is
// clicked. Shows the defanged domain, the live risk score, the per-component
// score breakdown (why the score is what it is), and — once the agent has run
// for this finding — its tool loop, recommended action, confidence,
// groundedness, and full brief.
//
// Driven entirely by the client SSE state already held in App (finding +
// agent). Props are shaped so a future real /api/agent/traces fetch can back the
// trace section without changing this component's render.

import { useEffect } from "react";
import type { AgentActivity, Finding } from "../App";
import { defang, riskColor } from "../lib";
import { COMPONENT_LABEL, TOOL_LABEL } from "../agentLabels";
import { Badge, RiskMeter } from "./ui";

function band(score: number): string {
  if (score >= 75) return "critical";
  if (score >= 55) return "high";
  if (score >= 35) return "medium";
  return "low";
}

function ComponentBar({ label, value }: { label: string; value: number }) {
  // Components are heterogeneous (0-100 similarity, small counts, 0/1 flags).
  // Normalize to a readable bar without implying a shared scale: cap at 100.
  const pct = Math.max(4, Math.min(100, value));
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span className="mono" style={{ fontSize: 12, color: "var(--text-dim)", width: 150 }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 6, background: "var(--bg-elevated)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: "var(--data)" }} />
      </div>
      <span className="mono" style={{ fontSize: 12, color: "var(--text)", width: 36, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
        {value}
      </span>
    </div>
  );
}

export function FindingDrawer({
  finding, agent, onClose,
}: { finding: Finding; agent?: AgentActivity; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const components = finding.components || {};
  const componentKeys = Object.keys(components);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
        display: "flex", justifyContent: "flex-end", zIndex: 50,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={`Finding detail for ${finding.domain}`}
        style={{
          width: 460, maxWidth: "90vw", height: "100%", overflow: "auto",
          background: "var(--bg-panel)", borderLeft: "1px solid var(--border)",
          padding: 24, display: "flex", flexDirection: "column", gap: 20,
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span className="mono" style={{ fontSize: 15 }}>{defang(finding.domain)}</span>
            <span className="mono" style={{ fontSize: 11, color: riskColor(finding.risk_score), textTransform: "uppercase", letterSpacing: 0.5 }}>
              {band(finding.risk_score)} risk
            </span>
          </div>
          <button onClick={onClose} className="mono" style={{
            fontSize: 12, color: "var(--text-dim)", background: "transparent",
            border: "1px solid var(--border)", borderRadius: "var(--r-sm)",
            padding: "4px 10px", cursor: "pointer",
          }}>close</button>
        </div>

        <RiskMeter score={finding.risk_score} />

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h3 className="display" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--text-dim)" }}>
            Score breakdown
          </h3>
          {componentKeys.length === 0 && (
            <p style={{ fontSize: 13, color: "var(--text-faint)" }}>No component data.</p>
          )}
          {componentKeys.map((k) => (
            <ComponentBar key={k} label={COMPONENT_LABEL[k] || k} value={components[k]} />
          ))}
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h3 className="display" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--text-dim)" }}>
            Agent investigation
          </h3>
          {!agent && (
            <p style={{ fontSize: 13, color: "var(--text-faint)" }}>
              No agent run for this finding yet.
            </p>
          )}
          {agent && (
            <>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
                <Badge plane="ai">agent</Badge>
                {agent.steps.map((s, i) => (
                  <span key={i} className="mono" style={{ fontSize: 11, color: "var(--ai)" }}>
                    {TOOL_LABEL[s] || s}{i < agent.steps.length - 1 ? " ·" : agent.done ? "" : " ..."}
                  </span>
                ))}
              </div>
              {agent.done && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {agent.recommended_action && (
                    <Badge plane="human">→ {agent.recommended_action} (tier {agent.tier})</Badge>
                  )}
                  {agent.confidence != null && (
                    <Badge plane="ai">conf {(agent.confidence * 100).toFixed(0)}%</Badge>
                  )}
                  {agent.groundedness != null && (
                    <Badge plane="data">grounded {(agent.groundedness * 100).toFixed(0)}%</Badge>
                  )}
                </div>
              )}
              {agent.done && agent.brief_excerpt && (
                <p style={{ fontSize: 13, color: "var(--text-dim)", whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
                  {agent.brief_excerpt}
                </p>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
