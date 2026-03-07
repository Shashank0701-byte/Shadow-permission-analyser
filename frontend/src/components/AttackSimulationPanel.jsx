import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL;

export default function AttackSimulationPanel({ user }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    fetch(`${API_BASE}/attack-simulation/${encodeURIComponent(user)}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [user]);

  if (!user) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🎭</div>
        <div className="empty-title">No Attack Simulation</div>
        <div className="empty-desc">Run a scan to simulate an attack path.</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="empty-state">
        <div className="empty-icon" style={{ animation: "pulse 1.5s infinite" }}>⏳</div>
        <div className="empty-title">Generating Attack Steps…</div>
      </div>
    );
  }

  if (!data || !data.steps || data.steps.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">✅</div>
        <div className="empty-title">No Attack Path</div>
        <div className="empty-desc">No exploitable escalation path found for {user}.</div>
      </div>
    );
  }

  return (
    <div style={{ padding: "1rem" }}>
      {/* Attack Path Summary */}
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
        <span style={{ fontSize: "1.2rem" }}>⚔️</span>
        <div>
          <div style={{
            fontSize: "0.65rem",
            fontWeight: 700,
            letterSpacing: "0.1em",
            color: "#f43f5e",
            textTransform: "uppercase",
            marginBottom: "0.2rem",
          }}>
            ATTACK PATH
          </div>
          <div style={{
            fontSize: "0.85rem",
            fontWeight: 600,
            color: "rgba(255,255,255,0.9)",
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            {data.attack_path}
          </div>
        </div>
      </div>

      {/* Attack Steps */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {data.steps.map((step, i) => (
          <div
            key={i}
            style={{
              background: "rgba(255,255,255,0.03)",
              borderRadius: "0.75rem",
              border: "1px solid rgba(255,255,255,0.06)",
              padding: "0.85rem 1rem",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {/* Step number badge */}
            <div style={{
              position: "absolute",
              top: 0,
              left: 0,
              background: step.action.includes("Mission Complete")
                ? "rgba(244, 63, 94, 0.3)"
                : "rgba(96, 165, 250, 0.15)",
              borderRadius: "0 0 0.5rem 0",
              padding: "0.15rem 0.5rem",
              fontSize: "0.6rem",
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: step.action.includes("Mission Complete") ? "#f43f5e" : "#60a5fa",
            }}>
              STEP {step.step}
            </div>

            <div style={{ marginTop: "1.2rem" }}>
              <div style={{
                fontSize: "0.8rem",
                fontWeight: 700,
                color: "rgba(255,255,255,0.95)",
                marginBottom: "0.3rem",
              }}>
                {step.action}
              </div>

              <div style={{
                fontSize: "0.72rem",
                color: "rgba(255,255,255,0.55)",
                marginBottom: "0.5rem",
              }}>
                {step.description}
              </div>

              {/* CLI Command */}
              <div style={{
                background: "rgba(0,0,0,0.4)",
                borderRadius: "0.5rem",
                padding: "0.6rem 0.75rem",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "0.62rem",
                color: "#34d399",
                lineHeight: 1.5,
                whiteSpace: "pre-wrap",
                overflowX: "auto",
                border: "1px solid rgba(52, 211, 153, 0.15)",
              }}>
                {step.cli_command}
              </div>

              {/* Risk + MITRE tag */}
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: "0.5rem",
                gap: "0.5rem",
                flexWrap: "wrap",
              }}>
                <span style={{
                  fontSize: "0.6rem",
                  color: step.risk.includes("CRITICAL") ? "#f43f5e" : "#fbbf24",
                  fontWeight: 600,
                }}>
                  ⚠️ {step.risk}
                </span>
                <span style={{
                  fontSize: "0.55rem",
                  background: "rgba(96, 165, 250, 0.1)",
                  border: "1px solid rgba(96, 165, 250, 0.2)",
                  borderRadius: "0.3rem",
                  padding: "0.15rem 0.4rem",
                  color: "#60a5fa",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {step.technique}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
