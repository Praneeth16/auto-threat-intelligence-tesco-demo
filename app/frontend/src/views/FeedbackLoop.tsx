// Feedback Loop: makes the learning loop visible. Two sections.
//
// 1. Routing map — pick a reason code, see where a reviewer's verdict is
//    written (eval / case memory / allowlist / policy store) and whether it
//    enters agent case memory. Read from the real reason_codes routing table
//    via the backend, so it never drifts from the code.
// 2. Post-feedback behavior — the compound beat: a policy_exception on
//    clubcard-summer writes an allowlist precedent; a later sibling
//    (clubcard-autumn) of the same signature AUTO-RESOLVES because the router
//    finds the precedent. No human needed the second time.

import { useEffect, useState } from "react";
import { api, defang } from "../lib";
import { Badge, Button, Panel } from "../components/ui";

const REASON_CODES = [
  "wrong_classification", "insufficient_evidence", "wrong_action", "policy_exception",
];

const DEST_LABEL: Record<string, string> = {
  eval_dataset: "Eval dataset",
  case_memory: "Agent case memory",
  policy_review: "Policy review",
  allowlist: "Allowlist (versioned)",
  policy_store: "Policy store",
};

interface Routing {
  reason_code: string;
  destinations: string[];
  enters_case_memory: boolean;
}

interface Sibling {
  signature: string;
  precedent_signature: string;
  matches: boolean;
  would_auto_resolve: boolean;
}

function Node({ label, plane }: { label: string; plane: string }) {
  return (
    <div style={{
      padding: "8px 14px", borderRadius: "var(--r-md)",
      border: `1px solid var(--${plane})`, background: "var(--bg-elevated)",
      color: "var(--text)", fontSize: 13,
    }}>{label}</div>
  );
}

export function FeedbackLoop() {
  const [code, setCode] = useState<string>("policy_exception");
  const [routing, setRouting] = useState<Routing | null>(null);
  const [sibling, setSibling] = useState<Sibling | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api.feedbackRouting(code).then(setRouting).catch(() => setRouting(null));
  }, [code]);

  const runSibling = async () => {
    setRunning(true);
    try {
      const res = await api.simulateSibling({
        campaign_id: "freshcart-phishops",
        recommended_action: "monitor",
        precedent_reason_code: "policy_exception",
      });
      setSibling(res);
      // Also fire the live override so the sibling shows up on the Live board.
      api.replayInject("clubcard-autumn").catch(() => {});
    } finally {
      setRunning(false);
    }
  };

  const isPolicyException = code === "policy_exception";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)", height: "100%", overflow: "auto" }}>
      <Panel title="Feedback routing — where a correction is written" plane="ai">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span className="mono" style={{ fontSize: 12, color: "var(--text-dim)" }}>reason code</span>
            {REASON_CODES.map((rc) => (
              <button
                key={rc}
                onClick={() => setCode(rc)}
                className="mono"
                style={{
                  fontSize: 12, padding: "6px 12px", borderRadius: "var(--r-sm)",
                  cursor: "pointer",
                  color: rc === code ? "var(--text)" : "var(--text-dim)",
                  background: rc === code ? "var(--bg-elevated)" : "transparent",
                  border: `1px solid ${rc === code ? "var(--ai)" : "var(--border)"}`,
                }}
              >{rc}</button>
            ))}
          </div>

          {routing && (
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <Node label={`verdict: ${routing.reason_code}`} plane="human" />
              <span style={{ color: "var(--text-faint)" }}>→</span>
              {routing.destinations.map((d) => (
                <Node key={d} label={DEST_LABEL[d] || d} plane="data" />
              ))}
              <Badge plane={routing.enters_case_memory ? "ai" : "neutral"}>
                enters agent case memory: {routing.enters_case_memory ? "yes" : "no"}
              </Badge>
            </div>
          )}

          {isPolicyException && (
            <p style={{ fontSize: 13, color: "var(--text-dim)", lineHeight: 1.5 }}>
              A <span style={{ color: "var(--ai)" }}>policy_exception</span> goes to the allowlist and
              policy store, <span style={{ color: "var(--human)" }}>not</span> agent case memory. The
              agent reasoned correctly on the evidence it had — teaching it a "lesson" here would
              train it to under-escalate similar domains. The fix is a policy fact, not agent memory.
            </p>
          )}
        </div>
      </Panel>

      <Panel title="Post-feedback behavior — a similar signal auto-resolves" plane="data">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <ol style={{ display: "flex", flexDirection: "column", gap: 10, listStyle: "none", padding: 0 }}>
            <li style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Badge plane="human">1</Badge>
              <span style={{ fontSize: 13 }}>
                Reviewer rejects {defang("clubcard-summer.tesco-clubcard-support.com")} as{" "}
                <span className="mono" style={{ color: "var(--ai)" }}>policy_exception</span> → writes an allowlist precedent.
              </span>
            </li>
            <li style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Badge plane="ai">2</Badge>
              <span style={{ fontSize: 13 }}>
                A sibling, {defang("clubcard-autumn.tesco-clubcard-support.com")}, arrives with the same campaign + action signature.
              </span>
            </li>
            <li style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Badge plane="data">3</Badge>
              <span style={{ fontSize: 13 }}>
                The router checks the allowlist by signature before escalating.
              </span>
            </li>
          </ol>

          <div>
            <Button plane="data" onClick={runSibling} disabled={running}>
              {running ? "checking precedent…" : "Trigger sibling signal"}
            </Button>
          </div>

          {sibling && (
            <div style={{
              border: `1px solid ${sibling.would_auto_resolve ? "var(--data)" : "var(--border)"}`,
              borderRadius: "var(--r-md)", padding: 14, background: "var(--bg-elevated)",
              display: "flex", flexDirection: "column", gap: 8,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Badge plane={sibling.would_auto_resolve ? "data" : "human"}>
                  {sibling.would_auto_resolve ? "AUTO-RESOLVED" : "escalated"}
                </Badge>
                <span style={{ fontSize: 13, color: "var(--text)" }}>
                  {sibling.would_auto_resolve
                    ? "Precedent found — the sibling closed with no human needed."
                    : "No precedent match — this would still escalate to a human."}
                </span>
              </div>
              <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>
                signature: {sibling.signature} {sibling.matches ? "== precedent" : "≠ precedent"}
              </span>
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}
