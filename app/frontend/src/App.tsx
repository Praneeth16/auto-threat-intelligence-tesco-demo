// SOC console shell. Holds the live state fed by SSE and lays out the four
// views on one situation board: Director Console (top control strip), Live
// Triage Board (center, the Act 2 centerpiece), Approval Queue (right, the
// human gate), Metrics Strip (bottom).

import { useCallback, useEffect, useState } from "react";
import { DirectorConsole } from "./views/DirectorConsole";
import { LiveTriage } from "./views/LiveTriage";
import { ExecutiveOverview } from "./views/ExecutiveOverview";
import { FeedbackLoop } from "./views/FeedbackLoop";
import { NavBar, type Tab } from "./components/NavBar";
import { useSSE } from "./sse";
import { api } from "./lib";

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

export interface Decision {
  decision_id: number;
  finding_id: string;
  route: string;
  tier: number;
  action: string;
}

export function App() {
  const [findings, setFindings] = useState<Record<string, Finding>>({});
  const [agents, setAgents] = useState<Record<string, AgentActivity>>({});
  const [tick, setTick] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [queueBump, setQueueBump] = useState(0);
  const [queuePending, setQueuePending] = useState(0);

  const onFinding = useCallback((d: Finding) => {
    setFindings((prev) => ({ ...prev, [d.finding_id]: { ...prev[d.finding_id], ...d } }));
  }, []);

  // Load any findings already in Lakebase on mount, so the board is not empty
  // before the stream starts.
  useEffect(() => {
    api.findings()
      .then((rows: Finding[]) => {
        setFindings((prev) => {
          const next = { ...prev };
          for (const f of rows) next[f.finding_id] = { ...next[f.finding_id], ...f };
          return next;
        });
      })
      .catch(() => {});
  }, []);

  const { connected } = useSSE({
    "replay.tick": setTick,
    "finding.updated": onFinding,
    "metrics.updated": setMetrics,
    "decision.routed": (d: Decision) => setDecision(d),
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

  const [activeTab, setActiveTab] = useState<Tab>("live");

  const findingList = Object.values(findings);
  const agentList = Object.values(agents);
  // The hero agent is analyzing when it has started but not completed and no
  // item is yet awaiting approval — the signal the queue placeholder shows.
  const analyzing = agentList.some((a) => !a.done) && queuePending === 0;

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      gap: "var(--gap)", padding: "var(--gap)", height: "100vh",
    }}>
      {/* Director Console + nav stay global: the run is the demo's clock and
          the presenter drives it from any tab. */}
      <DirectorConsole tick={tick} connected={connected} />
      <NavBar active={activeTab} onSelect={setActiveTab} />

      <div style={{ flex: 1, minHeight: 0 }}>
        {activeTab === "live" && (
          <LiveTriage
            findings={findingList} agents={agentList} decision={decision}
            metrics={metrics} tick={tick} queueBump={queueBump}
            queuePending={queuePending} analyzing={analyzing} onPending={setQueuePending}
          />
        )}
        {activeTab === "executive" && (
          <ExecutiveOverview findings={findingList} metrics={metrics} tick={tick} />
        )}
        {activeTab === "feedback" && <FeedbackLoop />}
      </div>
    </div>
  );
}
