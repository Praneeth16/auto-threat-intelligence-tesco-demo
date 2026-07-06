// SOC console shell. Holds the live state fed by SSE and lays out the four
// views on one situation board: Director Console (top control strip), Live
// Triage Board (center, the Act 2 centerpiece), Approval Queue (right, the
// human gate), Metrics Strip (bottom).

import { useCallback, useState } from "react";
import { DirectorConsole } from "./views/DirectorConsole";
import { TriageBoard } from "./views/TriageBoard";
import { ApprovalQueue } from "./views/ApprovalQueue";
import { MetricsStrip } from "./views/MetricsStrip";
import { useSSE } from "./sse";

export interface Finding {
  finding_id: string;
  domain: string;
  risk_score: number;
  components?: Record<string, number>;
  status: string;
}

export interface AgentActivity {
  agent_run_id: string;
  finding_id: string;
  steps: string[];
  brief_excerpt?: string;
  recommended_action?: string;
  tier?: number;
  confidence?: number;
  groundedness?: number;
  done: boolean;
}

export function App() {
  const [findings, setFindings] = useState<Record<string, Finding>>({});
  const [agents, setAgents] = useState<Record<string, AgentActivity>>({});
  const [tick, setTick] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [queueBump, setQueueBump] = useState(0);

  const onFinding = useCallback((d: Finding) => {
    setFindings((prev) => ({ ...prev, [d.finding_id]: { ...prev[d.finding_id], ...d } }));
  }, []);

  const { connected } = useSSE({
    "replay.tick": setTick,
    "finding.updated": onFinding,
    "metrics.updated": setMetrics,
    "agent.started": (d) =>
      setAgents((p) => ({ ...p, [d.agent_run_id]: {
        agent_run_id: d.agent_run_id, finding_id: d.finding_id, steps: [], done: false } })),
    "agent.step": (d) =>
      setAgents((p) => {
        const a = p[d.agent_run_id];
        if (!a) return p;
        return { ...p, [d.agent_run_id]: { ...a, steps: [...a.steps, d.tool] } };
      }),
    "agent.completed": (d) =>
      setAgents((p) => ({ ...p, [d.agent_run_id]: {
        ...(p[d.agent_run_id] || { agent_run_id: d.agent_run_id, finding_id: d.finding_id, steps: [] }),
        brief_excerpt: d.brief_excerpt, recommended_action: d.recommended_action,
        tier: d.tier, confidence: d.confidence, groundedness: d.groundedness, done: true } })),
    "queue.updated": () => setQueueBump((n) => n + 1),
  });

  return (
    <div style={{
      display: "grid",
      gridTemplateRows: "auto 1fr auto",
      gridTemplateColumns: "1fr 380px",
      gridTemplateAreas: `"director director" "board queue" "metrics metrics"`,
      gap: "var(--gap)", padding: "var(--gap)", height: "100vh",
    }}>
      <div style={{ gridArea: "director" }}>
        <DirectorConsole tick={tick} connected={connected} />
      </div>
      <div style={{ gridArea: "board", minHeight: 0 }}>
        <TriageBoard findings={Object.values(findings)} agents={Object.values(agents)} />
      </div>
      <div style={{ gridArea: "queue", minHeight: 0 }}>
        <ApprovalQueue bump={queueBump} />
      </div>
      <div style={{ gridArea: "metrics" }}>
        <MetricsStrip metrics={metrics} />
      </div>
    </div>
  );
}
