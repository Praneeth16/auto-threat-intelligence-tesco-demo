// Live Triage Board (PLAN 9.1 view 2, the Act 2 centerpiece): findings stream
// in with the risk score climbing live over SSE, the hero highlighted, campaign
// tags and source badges shown. When the agent fires, its lightweight step
// markers render inline ("querying telemetry..."); the full trace loads on
// completion.

import type { AgentActivity, Finding } from "../App";
import { defang } from "../lib";
import { Badge, Panel, RiskMeter } from "../components/ui";

const HERO = "tesco-clubcard-support.com";

const TOOL_LABEL: Record<string, string> = {
  query_telemetry: "querying telemetry",
  check_auth_anomalies: "checking auth anomalies",
  get_user_context: "reading user context",
  get_campaign_cluster: "clustering campaign",
  get_report_context: "pulling report context",
  search_case_memory: "searching case memory",
};

export function TriageBoard({ findings, agents }: { findings: Finding[]; agents: AgentActivity[] }) {
  const sorted = [...findings].sort((a, b) => b.risk_score - a.risk_score);
  const agentByFinding = Object.fromEntries(agents.map((a) => [a.finding_id, a]));

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
          return (
            <div key={f.finding_id} style={{
              border: `1px solid ${isHero ? "var(--human)" : "var(--border)"}`,
              borderRadius: "var(--r-md)", padding: "12px 14px",
              background: isHero ? "rgba(255,107,92,0.06)" : "var(--bg-elevated)",
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
    </Panel>
  );
}
