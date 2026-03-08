export default function WeakestUserPanel({ data }) {
    if (!data) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">🔍</div>
                <div className="empty-state-title">No Analysis Yet</div>
                <div className="empty-state-text">
                    Run a simulation to identify the weakest user in the IAM graph
                </div>
            </div>
        );
    }

    return (
        <div className="weakest-user-card">
            <div className="weakest-user-header">
                <div>
                    <div className="weakest-user-label">⚠ Highest Risk Account</div>
                    <div className="weakest-user-name">{data.user}</div>
                </div>
                <span className={`risk-badge ${(data.risk_level || "low").toLowerCase()}`}>
                    {data.risk_level || "LOW"}
                </span>
            </div>
            <div className="weakest-user-stats">
                <div className="wu-stat">
                    <div className="wu-stat-val" style={{ color: "#fb7185" }}>
                        {data.overall_risk_score}
                    </div>
                    <div className="wu-stat-label">Risk Score</div>
                </div>
                <div className="wu-stat">
                    <div className="wu-stat-val" style={{ color: "#fbbf24" }}>
                        {data.total_escalation_paths}
                    </div>
                    <div className="wu-stat-label">Esc. Paths</div>
                </div>
                <div className="wu-stat">
                    <div className="wu-stat-val" style={{ color: "#60a5fa" }}>
                        {data.max_depth}
                    </div>
                    <div className="wu-stat-label">Max Depth</div>
                </div>
            </div>
            {data.sensitive_targets && data.sensitive_targets.length > 0 && (
                <div style={{ marginTop: "0.85rem" }}>
                    <div
                        style={{
                            fontSize: "0.65rem",
                            color: "#64748b",
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                            fontWeight: 600,
                            marginBottom: "0.4rem",
                        }}
                    >
                        Sensitive Targets Reached
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                        {data.sensitive_targets.map((t) => (
                            <span key={t.name} className="path-node resource">
                                {t.name} (s:{t.sensitivity})
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
