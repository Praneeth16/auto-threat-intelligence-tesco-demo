// Approval Queue (PLAN 9.1 view 3, the human gate). Each item shows the agent
// brief, recommended action + tier, agent confidence, judge groundedness, and
// Approve/Reject with a reason-code selector. The action captures OBO identity
// server-side. The policy-exception reject on clubcard-summer is the Act 4 beat.

import { useEffect, useState } from "react";
import { api, defang } from "../lib";
import { Badge, Button, Panel } from "../components/ui";

const HERO_DOMAIN = "tesco-clubcard-support.com";

const REASON_CODES = [
  "wrong_classification", "insufficient_evidence", "wrong_action", "policy_exception",
];

interface QueueItem {
  queue_id: number;
  finding_id: string;
  brief: string;
  recommended_action: string;
  action_tier: number;
  agent_confidence: number;
  judge_groundedness: number;
  status: string;
}

export function ApprovalQueue({
  bump, analyzing = false, onPending,
}: { bump: number; analyzing?: boolean; onPending?: (n: number) => void }) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [reason, setReason] = useState<Record<number, string>>({});

  const load = () => api.queue().then(setItems).catch(() => setItems([]));
  useEffect(() => { load(); }, [bump]);

  const approve = async (id: number) => { await api.approve(id); load(); };
  const reject = async (id: number) => {
    const rc = reason[id] || "wrong_classification";
    await api.reject(id, rc); load();
  };

  const pending = items.filter((i) => i.status === "pending_review");

  // Report pending count up so StageFlow and the analyzing signal use the real
  // number rather than re-fetching.
  useEffect(() => { onPending?.(pending.length); }, [pending.length, onPending]);

  return (
    <Panel title="Approval queue" plane="human" right={<Badge plane="human">{pending.length} pending</Badge>}>
      {pending.length === 0 && analyzing && (
        <div style={{
          border: "1px dashed var(--ai)", borderRadius: "var(--r-md)",
          padding: 14, background: "var(--bg-elevated)",
          display: "flex", flexDirection: "column", gap: 6,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{
              width: 8, height: 8, borderRadius: 999, background: "var(--ai)",
              boxShadow: "0 0 8px var(--ai)",
            }} />
            <Badge plane="ai">agent working</Badge>
          </div>
          <p style={{ fontSize: 13, color: "var(--text-dim)" }}>
            Agent analyzing {defang(HERO_DOMAIN)} — recommendation pending review.
          </p>
        </div>
      )}
      {pending.length === 0 && !analyzing && (
        <p style={{ color: "var(--text-faint)" }}>Nothing awaiting approval.</p>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {pending.map((it) => (
          <div key={it.queue_id} style={{
            border: "1px solid var(--border)", borderRadius: "var(--r-md)",
            padding: 14, background: "var(--bg-elevated)",
          }}>
            <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
              <Badge plane="human">tier {it.action_tier}</Badge>
              <Badge plane="ai">{it.recommended_action}</Badge>
              {it.judge_groundedness != null && (
                <Badge plane="data">grounded {(it.judge_groundedness * 100).toFixed(0)}%</Badge>
              )}
              {it.agent_confidence != null && (
                <Badge plane="ai">conf {(it.agent_confidence * 100).toFixed(0)}%</Badge>
              )}
            </div>
            <p style={{ fontSize: 13, color: "var(--text-dim)", whiteSpace: "pre-wrap", marginBottom: 10 }}>
              {it.brief}
            </p>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <select value={reason[it.queue_id] || ""}
                onChange={(e) => setReason((r) => ({ ...r, [it.queue_id]: e.target.value }))}
                style={{
                  fontFamily: "var(--font-mono)", fontSize: 12, padding: "6px 8px",
                  background: "var(--bg)", color: "var(--text)",
                  border: "1px solid var(--border)", borderRadius: "var(--r-sm)",
                }}>
                <option value="">reason code…</option>
                {REASON_CODES.map((rc) => <option key={rc} value={rc}>{rc}</option>)}
              </select>
              <Button plane="data" onClick={() => approve(it.queue_id)}>Approve</Button>
              <Button plane="human" onClick={() => reject(it.queue_id)}>Reject</Button>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
