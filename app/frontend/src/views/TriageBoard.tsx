// Live Triage Board (PLAN 9.1 view 2, the Act 2 centerpiece): findings stream
// in with the risk score climbing live over SSE, the hero highlighted, campaign
// tags and source badges shown. When the agent fires, its lightweight step
// markers render inline ("querying telemetry..."); clicking a row opens the
// full detail drawer (score breakdown + agent trace + brief).

import { useState } from "react";
import type { AgentActivity, Finding } from "../App";
import { defang } from "../lib";
import { TOOL_LABEL } from "../agentLabels";
import { Badge, Panel, RiskMeter } from "../components/ui";
import { FindingDrawer } from "../components/FindingDrawer";

const HERO = "tesco-clubcard-support.com";

export function TriageBoard({ findings, agents }: { findings: Finding[]; agents: AgentActivity[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const sorted = [...findings].sort((a, b) => b.risk_score - a.risk_score);
  const agentByFinding = Object.fromEntries(agents.map((a) => [a.finding_id, a]));
  const selected = selectedId ? findings.find((f) => f.finding_id === selectedId) : undefined;

  return (
    <Panel title="Live triage board" plane="data" right={<Badge plane="data">{findings.length} findings</Badge>}>
      {sorted.length === 0 && (
        <p style={{ color: "var(--text-faint)" }}>
          No findings yet. Press Run on the Director Console to replay the attack.
        </p>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {sorted.map((f) => {
          const isHero = f.domain === HERO;
          const agent = agentByFinding[f.finding_id];
          const hovered = hoverId === f.finding_id;
          return (
            <div key={f.finding_id}
              role="button"
              tabIndex={0}
              aria-label={`Open detail for ${f.domain}`}
              onClick={() => setSelectedId(f.finding_id)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelectedId(f.finding_id); } }}
              onMouseEnter={() => setHoverId(f.finding_id)}
              onMouseLeave={() => setHoverId((h) => (h === f.finding_id ? null : h))}
              style={{
                border: `1px solid ${isHero ? "var(--human)" : hovered ? "var(--border-hi)" : "var(--border)"}`,
                borderRadius: "var(--r-md)", padding: "12px 14px",
                background: isHero ? "rgba(255,107,92,0.06)" : hovered ? "var(--bg-panel)" : "var(--bg-elevated)",
                cursor: "pointer", transition: "border-color 150ms, background 150ms",
              }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span className="mono" style={{ fontSize: 14, flex: 1 }}>
                  {defang(f.domain)}
                  {isHero && <span style={{ color: "var(--human)", marginLeft: 8, fontSize: 11 }}>HERO</span>}
                </span>
                <RiskMeter score={f.risk_score} />
              </div>
              {agent && (
                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
                  <Badge plane="ai">agent</Badge>
                  {agent.steps.map((s, i) => (
                    <span key={i} className="mono" style={{ fontSize: 11, color: "var(--ai)" }}>
                      {TOOL_LABEL[s] || s}{i < agent.steps.length - 1 ? " ·" : agent.done ? "" : " ..."}
                    </span>
                  ))}
                  {agent.done && agent.recommended_action && (
                    <Badge plane="human">→ {agent.recommended_action} (tier {agent.tier})</Badge>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {selected && (
        <FindingDrawer
          finding={selected}
          agent={agentByFinding[selected.finding_id]}
          onClose={() => setSelectedId(null)}
        />
      )}
    </Panel>
  );
}
