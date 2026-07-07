// Top navigation bar: switches the three console tabs. The active tab carries a
// plane-accent underline. Tab switching only swaps which view App renders — the
// SSE subscription and live state stay mounted in App, so the run keeps
// streaming while the presenter is on another tab.

export type Tab = "live" | "executive" | "feedback";

const TABS: { id: Tab; label: string; plane: string }[] = [
  { id: "live", label: "Live Triage", plane: "data" },
  { id: "executive", label: "Executive Overview", plane: "human" },
  { id: "feedback", label: "Feedback Loop", plane: "ai" },
];

export function NavBar({ active, onSelect }: { active: Tab; onSelect: (t: Tab) => void }) {
  return (
    <nav role="tablist" aria-label="SOC console views" style={{
      display: "flex", gap: 4, background: "var(--bg-panel)",
      border: "1px solid var(--border)", borderRadius: "var(--r-lg)",
      padding: 6,
    }}>
      {TABS.map((t) => {
        const isActive = t.id === active;
        const accent = `var(--${t.plane})`;
        return (
          <button
            key={t.id}
            role="tab"
            aria-selected={isActive}
            tabIndex={0}
            onClick={() => onSelect(t.id)}
            className="display"
            style={{
              flex: "0 0 auto", fontSize: 13, fontWeight: 600,
              padding: "8px 18px", borderRadius: "var(--r-md)", cursor: "pointer",
              color: isActive ? "var(--text)" : "var(--text-dim)",
              background: isActive ? "var(--bg-elevated)" : "transparent",
              border: `1px solid ${isActive ? accent : "transparent"}`,
              borderBottom: `2px solid ${isActive ? accent : "transparent"}`,
              transition: "color 150ms, background 150ms, border-color 150ms",
            }}
          >
            {t.label}
          </button>
        );
      })}
    </nav>
  );
}
