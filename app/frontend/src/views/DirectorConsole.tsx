// Director Console (PLAN 9.1 view 1): Run, Pause, Speed, force-path buttons (one
// per attack path + the clubcard-autumn sibling), and a Jump-to-decision beat
// control that fast-forwards the sim to the agent-fires point. Shows the sim
// clock and running state.

import { useState } from "react";
import { api } from "../lib";
import { Badge, Button } from "../components/ui";

const PATHS = ["AP1", "AP2", "AP3", "AP4", "AP5"];

export function DirectorConsole({ tick, connected }: { tick: any; connected: boolean }) {
  const [speed, setSpeed] = useState(720);
  const [running, setRunning] = useState(false);

  // The stream is the source of truth for running state: each replay.tick
  // carries it, so Run/Pause reflect what the backend simulator is actually
  // doing (and the button re-enables when the run completes on its own).
  const tickRunning = tick?.running;
  const effectiveRunning = tickRunning !== undefined ? tickRunning : running;

  const run = async () => { setRunning(true); await api.replayStart("full", speed); };
  const pause = async () => { setRunning(false); await api.replayPause(); };

  const simClock = tick?.sim_clock && tick.sim_clock !== "None" ? tick.sim_clock : "not started";

  return (
    <section style={{
      background: "var(--bg-panel)", border: "1px solid var(--border)",
      borderRadius: "var(--r-lg)", padding: "14px 18px",
      display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap",
    }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <span className="display" style={{ fontSize: 18, fontWeight: 700 }}>
          FreshCart PhishOps
        </span>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>
          72 hours on the lakehouse
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Button plane="data" onClick={run} disabled={effectiveRunning}>Run</Button>
        <Button plane="human" onClick={pause} disabled={!effectiveRunning}>Pause</Button>
        <label className="mono" style={{ fontSize: 12, color: "var(--text-dim)", display: "flex", alignItems: "center", gap: 6 }}>
          speed
          <input type="range" min={60} max={1440} step={60} value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))} />
          <span style={{ minWidth: 42 }}>{speed}x</span>
        </label>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>force path</span>
        {PATHS.map((p) => (
          <Button key={p} plane="ai" onClick={() => api.replayInject(p)}>{p}</Button>
        ))}
        <Button plane="ai" onClick={() => api.replayInject("clubcard-autumn")}>autumn</Button>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto" }}>
        <Button plane="human" onClick={() => api.replayJump()}>Jump to decision</Button>
        <Badge plane={connected ? "data" : "human"}>{connected ? "live" : "offline"}</Badge>
        <span className="mono" style={{ fontSize: 12, color: "var(--text-dim)" }}>{simClock}</span>
      </div>
    </section>
  );
}
