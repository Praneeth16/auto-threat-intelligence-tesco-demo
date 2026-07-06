// Metrics Strip (PLAN 9.1 view 4): counters (auto-resolved, auto-executed,
// queued), agent-human agreement rate, escalation rate, tokens/cost via the
// gateway. Updates on metrics.updated SSE events; falls back to a REST poll.

import { useEffect, useState } from "react";
import { api } from "../lib";

interface Metrics {
  auto_resolved?: number;
  auto_executed?: number;
  queued?: number;
  agreement_rate?: number;
  escalation_rate?: number;
  tokens?: number;
}

function Stat({ label, value, plane }: { label: string; value: string; plane: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 90 }}>
      <span className="display" style={{ fontSize: 24, fontWeight: 700, color: `var(--${plane})` }}>
        {value}
      </span>
      <span className="mono" style={{ fontSize: 10, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label}
      </span>
    </div>
  );
}

export function MetricsStrip({ metrics }: { metrics: Metrics | null }) {
  const [poll, setPoll] = useState<Metrics | null>(null);
  useEffect(() => {
    if (metrics) return;
    api.metrics().then(setPoll).catch(() => {});
  }, [metrics]);
  const m = metrics || poll || {};
  const pct = (v?: number) => (v == null ? "·" : `${(v * 100).toFixed(0)}%`);

  return (
    <section style={{
      background: "var(--bg-panel)", border: "1px solid var(--border)",
      borderRadius: "var(--r-lg)", padding: "14px 22px",
      display: "flex", alignItems: "center", gap: 32, flexWrap: "wrap",
    }}>
      <Stat label="auto-resolved" value={String(m.auto_resolved ?? 0)} plane="data" />
      <Stat label="auto-executed" value={String(m.auto_executed ?? 0)} plane="data" />
      <Stat label="queued" value={String(m.queued ?? 0)} plane="human" />
      <Stat label="agreement" value={pct(m.agreement_rate)} plane="ai" />
      <Stat label="escalation" value={pct(m.escalation_rate)} plane="ai" />
      <Stat label="tokens" value={m.tokens ? m.tokens.toLocaleString() : "·"} plane="data" />
    </section>
  );
}
