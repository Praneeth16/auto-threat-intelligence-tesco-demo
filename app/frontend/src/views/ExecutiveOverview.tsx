// Executive Overview: the leadership tab. Headline KPIs from live metrics, a
// campaign rollup (findings grouped hero vs tail with max risk), a risk-band
// distribution, and the Genie Q&A panel. Reads the same live state the operator
// board uses — leadership sees the "so what", operators see the board.

import type { Finding } from "../App";
import { riskColor } from "../lib";
import { Badge, Panel } from "../components/ui";
import { GeniePanel } from "../components/GeniePanel";

const HERO = "tesco-clubcard-support.com";

function Kpi({ label, value, plane }: { label: string; value: string; plane: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 120 }}>
      <span className="display" style={{ fontSize: 30, fontWeight: 700, color: `var(--${plane})`, fontVariantNumeric: "tabular-nums" }}>
        {value}
      </span>
      <span className="mono" style={{ fontSize: 10, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label}
      </span>
    </div>
  );
}

function band(score: number): "critical" | "high" | "medium" | "low" {
  if (score >= 75) return "critical";
  if (score >= 55) return "high";
  if (score >= 35) return "medium";
  return "low";
}

export function ExecutiveOverview({
  findings, metrics,
}: { findings: Finding[]; metrics: any; tick: any }) {
  const m = metrics || {};
  const pct = (v?: number) => (v == null ? "·" : `${(v * 100).toFixed(0)}%`);

  // Campaign rollup: this storyline is one campaign (FreshCart PhishOps); split
  // hero vs tail so leadership sees the headline threat and the cluster.
  const hero = findings.find((f) => f.domain === HERO);
  const tail = findings.filter((f) => f.domain !== HERO);
  const maxTail = tail.reduce((mx, f) => Math.max(mx, f.risk_score), 0);

  // Risk-band distribution across all findings.
  const bands = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const f of findings) bands[band(f.risk_score)]++;
  const bandOrder: (keyof typeof bands)[] = ["critical", "high", "medium", "low"];
  const bandColor = { critical: "var(--risk-crit)", high: "var(--risk-high)", medium: "var(--risk-mid)", low: "var(--risk-low)" };
  const maxBand = Math.max(1, ...Object.values(bands));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)", height: "100%", overflow: "auto" }}>
      <Panel title="Executive summary" plane="human">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 32 }}>
          <Kpi label="events" value={m.events_total ? m.events_total.toLocaleString() : "0"} plane="data" />
          <Kpi label="anomalies" value={String(m.anomalies ?? findings.length)} plane="human" />
          <Kpi label="auto-resolved" value={String((m.auto_resolved ?? 0) + (m.auto_executed ?? 0))} plane="data" />
          <Kpi label="human-queued" value={String(m.queued ?? 0)} plane="human" />
          <Kpi label="agreement" value={pct(m.agreement_rate)} plane="ai" />
          <Kpi label="escalation" value={pct(m.escalation_rate)} plane="ai" />
          <Kpi label="tokens" value={m.tokens ? m.tokens.toLocaleString() : "·"} plane="data" />
        </div>
      </Panel>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--gap)" }}>
        <Panel title="Campaign rollup" plane="data">
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span className="display" style={{ fontSize: 15, fontWeight: 700 }}>FreshCart PhishOps</span>
                <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>
                  {findings.length} lookalike domains · 1 hero · {tail.length} tail
                </span>
              </div>
              <Badge plane="human">active</Badge>
            </div>
            <div style={{ display: "flex", gap: 20 }}>
              <div>
                <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>HERO MAX RISK</span>
                <div className="display" style={{ fontSize: 24, fontWeight: 700, color: riskColor(hero?.risk_score ?? 0) }}>
                  {hero ? hero.risk_score.toFixed(0) : "·"}
                </div>
              </div>
              <div>
                <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>TAIL MAX RISK</span>
                <div className="display" style={{ fontSize: 24, fontWeight: 700, color: riskColor(maxTail) }}>
                  {maxTail ? maxTail.toFixed(0) : "·"}
                </div>
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="Risk distribution" plane="human">
          {findings.length === 0 && <p style={{ color: "var(--text-faint)" }}>No findings yet.</p>}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {bandOrder.map((b) => (
              <div key={b} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span className="mono" style={{ fontSize: 12, color: "var(--text-dim)", width: 72, textTransform: "capitalize" }}>{b}</span>
                <div style={{ flex: 1, height: 10, background: "var(--bg-elevated)", borderRadius: 999, overflow: "hidden" }}>
                  <div style={{ width: `${(bands[b] / maxBand) * 100}%`, height: "100%", background: bandColor[b] }} />
                </div>
                <span className="mono" style={{ fontSize: 12, color: "var(--text)", width: 20, textAlign: "right" }}>{bands[b]}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <GeniePanel />
    </div>
  );
}
