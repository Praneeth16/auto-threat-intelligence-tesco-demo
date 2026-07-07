// Genie Q&A panel for the Executive Overview. Ask a natural-language question
// over the SOC datasets; the backend answers via live Databricks Genie
// in-workspace or a deterministic scripted answer offline. A source badge keeps
// the demo honest about which path served the answer.

import { useState } from "react";
import { api } from "../lib";
import { Badge, Button, Panel } from "./ui";

const SUGGESTIONS = [
  "What's the top campaign?",
  "How many anomalies?",
  "What's the hero finding?",
  "How much did the auto lane resolve?",
];

interface Answer {
  answer: string;
  source: string;
  sql?: string;
  rows?: any[];
}

function SourceBadge({ source }: { source: string }) {
  const live = source === "genie";
  return <Badge plane={live ? "data" : "ai"}>{live ? "genie" : source}</Badge>;
}

export function GeniePanel() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (q: string) => {
    const query = q.trim();
    if (!query) return;
    setLoading(true); setError(null);
    try {
      const res = await api.genieAsk(query);
      setAnswer(res);
    } catch {
      setError("Genie request failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel title="Ask Genie" plane="data" right={answer && <SourceBadge source={answer.source} />}>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <form
          onSubmit={(e) => { e.preventDefault(); ask(question); }}
          style={{ display: "flex", gap: 8 }}
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about the SOC datasets…"
            aria-label="Genie question"
            style={{
              flex: 1, fontFamily: "var(--font-body)", fontSize: 13,
              padding: "8px 12px", background: "var(--bg)", color: "var(--text)",
              border: "1px solid var(--border)", borderRadius: "var(--r-sm)",
            }}
          />
          <Button plane="data" disabled={loading || !question.trim()}>
            {loading ? "asking…" : "Ask"}
          </Button>
        </form>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => { setQuestion(s); ask(s); }}
              className="mono"
              style={{
                fontSize: 11, padding: "4px 10px", borderRadius: 999,
                color: "var(--text-dim)", background: "transparent",
                border: "1px solid var(--border)", cursor: "pointer",
              }}
            >{s}</button>
          ))}
        </div>

        {error && <p style={{ color: "var(--human)", fontSize: 13 }}>{error}</p>}

        {answer && !error && (
          <div style={{
            border: "1px solid var(--border)", borderRadius: "var(--r-md)",
            padding: 14, background: "var(--bg-elevated)",
            display: "flex", flexDirection: "column", gap: 10,
          }}>
            <p style={{ fontSize: 13, color: "var(--text)", whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
              {answer.answer}
            </p>
            {answer.sql && (
              <pre className="mono" style={{
                fontSize: 11, color: "var(--text-dim)", background: "var(--bg)",
                padding: 10, borderRadius: "var(--r-sm)", overflow: "auto", margin: 0,
              }}>{answer.sql}</pre>
            )}
            {answer.rows && answer.rows.length > 0 && (
              <div style={{ overflow: "auto" }}>
                <table className="mono" style={{ fontSize: 12, borderCollapse: "collapse", width: "100%" }}>
                  <thead>
                    <tr>
                      {Object.keys(answer.rows[0]).map((k) => (
                        <th key={k} style={{ textAlign: "left", padding: "4px 8px", color: "var(--text-dim)", borderBottom: "1px solid var(--border)" }}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {answer.rows.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((v, j) => (
                          <td key={j} style={{ padding: "4px 8px", color: "var(--text)", borderBottom: "1px solid var(--border)" }}>{String(v)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
