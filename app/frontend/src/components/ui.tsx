// Shared UI primitives. The RiskMeter is the signature element: a bar that
// animates as the hero finding's score climbs on live SSE updates.

import type { ReactNode } from "react";
import { riskColor } from "../lib";

type Plane = "data" | "ai" | "human" | "neutral";

const planeColor: Record<Plane, string> = {
  data: "var(--data)",
  ai: "var(--ai)",
  human: "var(--human)",
  neutral: "var(--text-dim)",
};

export function Panel({
  title, plane = "neutral", children, right,
}: { title: string; plane?: Plane; children: ReactNode; right?: ReactNode }) {
  return (
    <section style={{
      background: "var(--bg-panel)",
      border: "1px solid var(--border)",
      borderRadius: "var(--r-lg)",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    }}>
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px 16px", borderBottom: "1px solid var(--border)",
        borderLeft: `3px solid ${planeColor[plane]}`,
      }}>
        <h2 className="display" style={{
          fontSize: 13, fontWeight: 600, letterSpacing: 0.5,
          textTransform: "uppercase", color: "var(--text-dim)",
        }}>{title}</h2>
        {right}
      </header>
      <div style={{ padding: 16, overflow: "auto", flex: 1 }}>{children}</div>
    </section>
  );
}

export function Badge({ children, plane = "neutral" }: { children: ReactNode; plane?: Plane }) {
  return (
    <span className="mono" style={{
      fontSize: 11, padding: "2px 8px", borderRadius: 999,
      color: planeColor[plane], border: `1px solid ${planeColor[plane]}`,
      background: "transparent", whiteSpace: "nowrap",
    }}>{children}</span>
  );
}

export function RiskMeter({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  const color = riskColor(score);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 160 }}>
      <div style={{
        flex: 1, height: 8, background: "var(--bg-elevated)",
        borderRadius: 999, overflow: "hidden",
      }}>
        <div style={{
          width: `${pct}%`, height: "100%", background: color,
          transition: "width 600ms cubic-bezier(.2,.8,.2,1), background 600ms",
        }} />
      </div>
      <span className="display" style={{
        fontSize: 20, fontWeight: 700, color, minWidth: 44, textAlign: "right",
        fontVariantNumeric: "tabular-nums",
      }}>{score.toFixed(0)}</span>
    </div>
  );
}

export function Button({
  children, onClick, plane = "neutral", disabled,
}: { children: ReactNode; onClick?: () => void; plane?: Plane; disabled?: boolean }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600,
      padding: "8px 14px", borderRadius: "var(--r-sm)", cursor: disabled ? "default" : "pointer",
      color: disabled ? "var(--text-faint)" : planeColor[plane],
      background: "transparent",
      border: `1px solid ${disabled ? "var(--border)" : planeColor[plane]}`,
      opacity: disabled ? 0.5 : 1,
    }}>{children}</button>
  );
}
