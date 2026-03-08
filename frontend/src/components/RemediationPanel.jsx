import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL;

const PRIORITY_COLORS = {
  CRITICAL: { bg: "rgba(244, 63, 94, 0.1)", border: "rgba(244, 63, 94, 0.3)", text: "#f43f5e" },
  HIGH: { bg: "rgba(251, 146, 60, 0.1)", border: "rgba(251, 146, 60, 0.3)", text: "#fb923c" },
  MEDIUM: { bg: "rgba(251, 191, 36, 0.1)", border: "rgba(251, 191, 36, 0.3)", text: "#fbbf24" },
  LOW: { bg: "rgba(52, 211, 153, 0.1)", border: "rgba(52, 211, 153, 0.3)", text: "#34d399" },
};

export default function RemediationPanel({ user }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    fetch(`${API_BASE}/remediation/${encodeURIComponent(user)}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [user]);

  if (!user) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🛠️</div>
        <div className="empty-title">No Remediation Data</div>
        <div className="empty-desc">Run a scan to generate fix suggestions.</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="empty-state">
        <div className="empty-icon" style={{ animation: "pulse 1.5s infinite" }}>⏳</div>
        <div className="empty-title">Generating Fixes…</div>
      </div>
    );
  }

  if (!data || !data.recommendations || data.recommendations.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">✅</div>
        <div className="empty-title">No Fixes Needed</div>
        <div className="empty-desc">No escalation risks found for {user}.</div>
      </div>
    );
  }

  return (
    <div style={{ padding: "1rem" }}>
      {/* Weakest Edge Summary */}
      {data.weakest_edge && (
        <div style={{
          background: "rgba(244, 63, 94, 0.08)",
          border: "1px solid rgba(244, 63, 94, 0.25)",
          borderRadius: "0.75rem",
          padding: "0.85rem 1rem",
          marginBottom: "1rem",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
        }}>
          <span style={{ fontSize: "1.2rem" }}>🎯</span>
          <div>
            <div style={{
              fontSize: "0.65rem",
              fontWeight: 700,
              letterSpacing: "0.1em",
              color: "#f43f5e",
              textTransform: "uppercase",
              marginBottom: "0.2rem",
            }}>
              WEAKEST EDGE — REMOVE THIS TO BREAK THE CHAIN
            </div>
            <div style={{
              fontSize: "0.85rem",
              fontWeight: 600,
              color: "rgba(255,255,255,0.9)",
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              {data.weakest_edge.source} —[{data.weakest_edge.type}]→ {data.weakest_edge.target}
            </div>
            <div style={{
              fontSize: "0.62rem",
              color: "rgba(255,255,255,0.4)",
              marginTop: "0.15rem",
            }}>
              Hop {data.weakest_edge.position} of {data.weakest_edge.total_hops} in the escalation chain
            </div>
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {data.recommendations.map((rec, i) => {
          const pColor = PRIORITY_COLORS[rec.priority] || PRIORITY_COLORS.LOW;
          return (
            <div
              key={i}
              style={{
                background: pColor.bg,
                borderRadius: "0.75rem",
                border: `1px solid ${pColor.border}`,
                padding: "0.85rem 1rem",
              }}
            >
              {/* Priority badge + title */}
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                marginBottom: "0.4rem",
              }}>
                <span style={{
                  fontSize: "0.55rem",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  color: pColor.text,
                  background: `${pColor.bg}`,
                  border: `1px solid ${pColor.border}`,
                  borderRadius: "0.3rem",
                  padding: "0.1rem 0.35rem",
                  textTransform: "uppercase",
                }}>
                  {rec.priority}
                </span>
                <span style={{
                  fontSize: "0.78rem",
                  fontWeight: 700,
                  color: "rgba(255,255,255,0.9)",
                }}>
                  {rec.title}
                </span>
              </div>

              <div style={{
                fontSize: "0.7rem",
                color: "rgba(255,255,255,0.55)",
                marginBottom: "0.5rem",
                lineHeight: 1.45,
              }}>
                {rec.description}
              </div>

              {/* CLI fix command */}
              <div style={{
                background: "rgba(0,0,0,0.4)",
                borderRadius: "0.5rem",
                padding: "0.6rem 0.75rem",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "0.6rem",
                color: "#34d399",
                lineHeight: 1.5,
                whiteSpace: "pre-wrap",
                overflowX: "auto",
                border: "1px solid rgba(52, 211, 153, 0.15)",
              }}>
                {rec.aws_cli}
              </div>

              <div style={{
                fontSize: "0.6rem",
                color: pColor.text,
                fontWeight: 600,
                marginTop: "0.4rem",
              }}>
                💡 Impact: {rec.impact}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
