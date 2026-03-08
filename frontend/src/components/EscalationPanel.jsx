function getRiskClass(score) {
    if (score >= 60) return "critical";
    if (score >= 40) return "high";
    if (score >= 20) return "medium";
    return "low";
}

export default function EscalationPanel({ data }) {
    if (!data || data.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">📈</div>
                <div className="empty-state-title">No Escalation Data</div>
                <div className="empty-state-text">
                    Run a simulation to analyze privilege escalation paths
                </div>
            </div>
        );
    }

    // Sort users by risk score descending
    const sorted = [...data].sort(
        (a, b) => (b.overall_risk_score || 0) - (a.overall_risk_score || 0)
    );

    return (
        <table className="escalation-table">
            <thead>
                <tr>
                    <th>User</th>
                    <th>Risk Level</th>
                    <th>Risk Score</th>
                    <th>Paths</th>
                    <th>Max Depth</th>
                    <th>Escalation Chain</th>
                </tr>
            </thead>
            <tbody>
                {sorted.map((u) => {
                    const score = u.overall_risk_score || 0;
                    const riskClass = getRiskClass(score);
                    // Show the first path chain if available
                    const firstPath =
                        u.escalation_paths && u.escalation_paths.length > 0
                            ? u.escalation_paths[0]
                            : null;

                    return (
                        <tr key={u.user}>
                            <td className="mono" style={{ fontWeight: 600, color: "#f1f5f9" }}>
                                {u.user}
                            </td>
                            <td>
                                <span className={`risk-badge ${(u.risk_level || "low").toLowerCase()}`}>
                                    {u.risk_level || "LOW"}
                                </span>
                            </td>
                            <td>
                                <div className="risk-score-bar">
                                    <div className="risk-bar-track">
                                        <div
                                            className={`risk-bar-fill ${riskClass}`}
                                            style={{ width: `${Math.min(score, 100)}%` }}
                                        />
                                    </div>
                                    <span
                                        className="risk-score-value"
                                        style={{
                                            color:
                                                score >= 60
                                                    ? "#fb7185"
                                                    : score >= 40
                                                        ? "#fbbf24"
                                                        : score >= 20
                                                            ? "#60a5fa"
                                                            : "#34d399",
                                        }}
                                    >
                                        {score}
                                    </span>
                                </div>
                            </td>
                            <td className="mono">{u.total_paths}</td>
                            <td className="mono">{u.max_depth}</td>
                            <td>
                                {firstPath ? (
                                    <div className="path-chain">
                                        {firstPath.nodes.map((node, i) => (
                                            <span key={i}>
                                                <span
                                                    className={`path-node ${(node.label || "unknown").toLowerCase()}`}
                                                >
                                                    {node.name}
                                                </span>
                                                {i < firstPath.nodes.length - 1 && (
                                                    <span className="path-arrow"> → </span>
                                                )}
                                            </span>
                                        ))}
                                    </div>
                                ) : (
                                    <span style={{ color: "#64748b", fontSize: "0.72rem" }}>
                                        No paths
                                    </span>
                                )}
                            </td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}
