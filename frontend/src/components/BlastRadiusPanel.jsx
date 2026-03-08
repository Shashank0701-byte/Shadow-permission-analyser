export default function BlastRadiusPanel({ data }) {
    if (!data || data.total_affected_resources === 0) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">💥</div>
                <div className="empty-state-title">No Blast Radius Data</div>
                <div className="empty-state-text">
                    Run a simulation to compute the blast radius
                </div>
            </div>
        );
    }

    return (
        <table className="escalation-table">
            <thead>
                <tr>
                    <th>Resource</th>
                    <th>Sensitivity</th>
                    <th>Min Path Length</th>
                    <th>Risk Score</th>
                </tr>
            </thead>
            <tbody>
                {(data?.affected_resources ?? []).map((r) => {
                    const riskClass =
                        r.risk_score >= 8
                            ? "critical"
                            : r.risk_score >= 6
                                ? "high"
                                : r.risk_score >= 3
                                    ? "medium"
                                    : "low";

                    return (
                        <tr key={r.name}>
                            <td>
                                <span className="path-node resource">{r.name}</span>
                            </td>
                            <td>
                                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                                    {[...Array(5)].map((_, i) => (
                                        <span
                                            key={i}
                                            style={{
                                                width: 8,
                                                height: 8,
                                                borderRadius: "50%",
                                                background:
                                                    i < r.sensitivity
                                                        ? r.sensitivity >= 4
                                                            ? "#fb7185"
                                                            : r.sensitivity >= 3
                                                                ? "#fbbf24"
                                                                : "#34d399"
                                                        : "rgba(255,255,255,0.08)",
                                                display: "inline-block",
                                            }}
                                        />
                                    ))}
                                    <span className="mono" style={{ fontSize: "0.7rem", marginLeft: "0.3rem" }}>
                                        {r.sensitivity}/5
                                    </span>
                                </div>
                            </td>
                            <td className="mono">{r.min_path_length} hops</td>
                            <td>
                                <div className="risk-score-bar">
                                    <div className="risk-bar-track">
                                        <div
                                            className={`risk-bar-fill ${riskClass}`}
                                            style={{ width: `${(r.risk_score / 10) * 100}%` }}
                                        />
                                    </div>
                                    <span
                                        className="risk-score-value"
                                        style={{
                                            color:
                                                r.risk_score >= 8
                                                    ? "#fb7185"
                                                    : r.risk_score >= 6
                                                        ? "#fbbf24"
                                                        : r.risk_score >= 3
                                                            ? "#60a5fa"
                                                            : "#34d399",
                                        }}
                                    >
                                        {r.risk_score}
                                    </span>
                                </div>
                            </td>
                        </tr>
                    );
                })}
            </tbody>
            <tfoot>
                <tr>
                    <td
                        colSpan={4}
                        style={{
                            padding: "0.85rem",
                            background: "rgba(0,0,0,0.15)",
                            borderTop: "1px solid rgba(99,102,241,0.1)",
                        }}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                                Aggregate Risk Score
                            </span>
                            <span
                                style={{
                                    fontSize: "1rem",
                                    fontWeight: 800,
                                    fontFamily: "'JetBrains Mono', monospace",
                                    color:
                                        data.aggregate_risk_score >= 8
                                            ? "#fb7185"
                                            : data.aggregate_risk_score >= 6
                                                ? "#fbbf24"
                                                : data.aggregate_risk_score >= 3
                                                    ? "#60a5fa"
                                                    : "#34d399",
                                }}
                            >
                                {data.aggregate_risk_score} / 10
                            </span>
                        </div>
                    </td>
                </tr>
            </tfoot>
        </table>
    );
}
