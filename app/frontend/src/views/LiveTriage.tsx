// Live Triage view: the operator's situation board — StageFlow strip, Triage
// Board (center), Approval Queue (right), Metrics (bottom). Extracted from App
// so the tab shell can swap it out; App still owns the live state and feeds it
// in as props. The Director Console is rendered globally by App, above the tabs.

import type { AgentActivity, Decision, Finding } from "../App";
import { StageFlow } from "../components/StageFlow";
import { TriageBoard } from "./TriageBoard";
import { ApprovalQueue } from "./ApprovalQueue";
import { MetricsStrip } from "./MetricsStrip";

export function LiveTriage({
  findings, agents, decision, metrics, tick,
  queueBump, queuePending, analyzing, onPending,
}: {
  findings: Finding[];
  agents: AgentActivity[];
  decision: Decision | null;
  metrics: any;
  tick: any;
  queueBump: number;
  queuePending: number;
  analyzing: boolean;
  onPending: (n: number) => void;
}) {
  return (
    <div style={{
      display: "grid",
      gridTemplateRows: "auto 1fr auto",
      gridTemplateColumns: "1fr 380px",
      gridTemplateAreas: `"stages stages" "board queue" "metrics metrics"`,
      gap: "var(--gap)", height: "100%", minHeight: 0,
    }}>
      <div style={{ gridArea: "stages" }}>
        <StageFlow
          tick={tick} findings={findings} agents={agents}
          decision={decision} queuePending={queuePending} metrics={metrics}
        />
      </div>
      <div style={{ gridArea: "board", minHeight: 0 }}>
        <TriageBoard findings={findings} agents={agents} />
      </div>
      <div style={{ gridArea: "queue", minHeight: 0 }}>
        <ApprovalQueue bump={queueBump} analyzing={analyzing} onPending={onPending} />
      </div>
      <div style={{ gridArea: "metrics" }}>
        <MetricsStrip metrics={metrics} />
      </div>
    </div>
  );
}
