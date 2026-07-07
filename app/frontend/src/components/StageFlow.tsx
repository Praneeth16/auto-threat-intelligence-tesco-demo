// Stage-flow strip: the six pipeline stages the demo narrates, lit up live so an
// audience can see where the storyline is. Status (idle / active / done) is
// derived entirely from state already in App — no new SSE event types. The one
// client addition it depends on is App's decision.routed handler.

import type { AgentActivity, Decision, Finding } from "../App";

type Status = "idle" | "active" | "done";

const HERO = "tesco-clubcard-support.com";
const HERO_PEAK = 82; // baked hero final score (see app/backend/simulator.py)

const PLANE: Record<string, string> = {
  Telemetry: "data", Findings: "human", Agent: "ai",
  Decision: "ai", Approval: "human", Metrics: "data",
};

function statusColor(plane: string, status: Status): string {
  if (status === "idle") return "var(--text-faint)";
  return `var(--${plane})`;
}

interface Props {
  tick: any;
  findings: Finding[];
  agents: AgentActivity[];
  decision: Decision | null;
  queuePending: number;
  metrics: any;
}

function deriveStages(p: Props): { name: string; status: Status }[] {
  const running = p.tick?.running === true;
  const started = p.tick != null && (p.tick.running !== undefined);
  const completed = p.tick != null && p.tick.running === false && p.tick.sim_clock != null;

  const maxScore = p.findings.reduce((m, f) => Math.max(m, f.risk_score), 0);
  const heroAgent = p.agents.find((a) => a.finding_id.includes("clubcard-support") || a.finding_id === HERO) || p.agents[0];
  const anyAgentRunning = p.agents.some((a) => !a.done);
  const anyAgentDone = p.agents.some((a) => a.done);

  const telemetry: Status = completed ? "done" : running ? "active" : "idle";
  const findings: Status = p.findings.length === 0 ? "idle" : maxScore >= HERO_PEAK ? "done" : "active";
  const agent: Status = anyAgentDone ? "done" : anyAgentRunning ? "active" : "idle";
  const decision: Status = p.decision ? "done" : anyAgentDone ? "active" : "idle";
  const approval: Status = p.queuePending > 0 ? "active" : p.decision && p.queuePending === 0 && anyAgentDone ? "done" : "idle";
  const metrics: Status = completed ? "done" : (p.metrics?.tokens ?? 0) > 0 ? "active" : "idle";

  // Reference heroAgent/started so the intent is explicit even where the simpler
  // any-agent signals already cover the demo's single-hero storyline.
  void heroAgent; void started;

  return [
    { name: "Telemetry", status: telemetry },
    { name: "Findings", status: findings },
    { name: "Agent", status: agent },
    { name: "Decision", status: decision },
    { name: "Approval", status: approval },
    { name: "Metrics", status: metrics },
  ];
}

export function StageFlow(props: Props) {
  const stages = deriveStages(props);

  return (
    <section style={{
      background: "var(--bg-panel)", border: "1px solid var(--border)",
      borderRadius: "var(--r-lg)", padding: "12px 18px",
      display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap",
    }}>
      {stages.map((s, i) => {
        const plane = PLANE[s.name];
        const color = statusColor(plane, s.status);
        return (
          <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "6px 12px", borderRadius: 999,
              border: `1px solid ${s.status === "idle" ? "var(--border)" : color}`,
              background: s.status === "active" ? "rgba(255,255,255,0.03)" : "transparent",
              opacity: s.status === "idle" ? 0.5 : 1,
              transition: "opacity 300ms, border-color 300ms",
            }}>
              <span style={{
                width: 8, height: 8, borderRadius: 999, background: color,
                boxShadow: s.status === "active" ? `0 0 8px ${color}` : "none",
              }} />
              <span className="mono" style={{ fontSize: 12, color: s.status === "idle" ? "var(--text-faint)" : "var(--text)" }}>
                {s.name}
              </span>
              {s.status === "done" && (
                <span className="mono" style={{ fontSize: 11, color }}>✓</span>
              )}
            </div>
            {i < stages.length - 1 && (
              <span style={{ color: "var(--text-faint)", fontSize: 12 }}>›</span>
            )}
          </div>
        );
      })}
    </section>
  );
}
