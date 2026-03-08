export default function CentralityPanel({ data }) {
    if (!data) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">🎯</div>
                <div className="empty-state-title">No Analysis Yet</div>
                <div className="empty-state-text">
                    Run a simulation to find critical nodes
                </div>
            </div>
        );
    }

    const bridges = data.critical_bridges || [];
    const hubs = data.critical_hubs || [];
    const maxScore = Math.max(
        ...hubs.map((h) => h.betweenness_centrality),
        0.01
    );

    return (
        <div>
            {/* Critical Bridges — THE key answer */}
            {bridges.length > 0 && (
                <div style={{ marginBottom: "1.2rem" }}>
                    <div
                        style={{
                            fontSize: "0.65rem",
                            textTransform: "uppercase",
                            letterSpacing: "0.1em",
                            color: "#fb7185",
                            fontWeight: 700,
                            marginBottom: "0.6rem",
                            display: "flex",
                            alignItems: "center",
                            gap: "0.4rem",
                        }}
                    >
                        🚨 Critical Bridge Nodes
                        <span
                            style={{
                                fontSize: "0.6rem",
                                fontWeight: 400,
                                color: "#94a3b8",
                                textTransform: "none",
                                letterSpacing: "normal",
                            }}
                        >
                            — removing these breaks escalation paths
                        </span>
                    </div>
                    {bridges.map((bridge, i) => (
                        <div
                            key={bridge.id}
                            style={{
                                background:
                                    "linear-gradient(135deg, rgba(244,63,94,0.08) 0%, rgba(99,102,241,0.05) 100%)",
                                border: "1px solid rgba(244,63,94,0.2)",
                                borderRadius: "var(--radius-sm)",
                                padding: "0.85rem 1rem",
                                marginBottom: "0.5rem",
                            }}
                        >
                            <div
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    marginBottom: "0.5rem",
                                }}
                            >
                                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                    <div className="hub-rank">{i + 1}</div>
                                    <span
                                        className="hub-name"
                                        style={{ color: "#f1f5f9", fontSize: "0.9rem" }}
                                    >
                                        {bridge.name}
                                    </span>
                                </div>
                                <span className="risk-badge critical">
                                    {bridge.impact}% impact
                                </span>
                            </div>
                            <div
                                style={{
                                    fontSize: "0.7rem",
                                    color: "#94a3b8",
                                    marginBottom: "0.4rem",
                                }}
                            >
                                Breaks{" "}
                                <strong style={{ color: "#fb7185" }}>
                                    {bridge.paths_broken}
                                </strong>{" "}
                                escalation path{bridge.paths_broken !== 1 ? "s" : ""}
                            </div>
                            {bridge.broken_connections &&
                                bridge.broken_connections.length > 0 && (
                                    <div
                                        style={{
                                            display: "flex",
                                            flexWrap: "wrap",
                                            gap: "0.35rem",
                                        }}
                                    >
                                        {bridge.broken_connections.map((conn, j) => (
                                            <div
                                                key={j}
                                                style={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    gap: "0.25rem",
                                                }}
                                            >
                                                <span className="path-node user">{conn.user}</span>
                                                <span className="path-arrow">✕</span>
                                                <span className="path-node resource">
                                                    {conn.resource}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                        </div>
                    ))}
                </div>
            )}

            {/* Centrality Ranking */}
            {hubs.length > 0 && (
                <div>
                    <div
                        style={{
                            fontSize: "0.65rem",
                            textTransform: "uppercase",
                            letterSpacing: "0.1em",
                            color: "#64748b",
                            fontWeight: 600,
                            marginBottom: "0.5rem",
                        }}
                    >
                        Betweenness Centrality Ranking
                    </div>
                    <div className="hub-list">
                        {hubs.map((hub, i) => (
                            <div key={hub.id} className="hub-item">
                                <div className="hub-info">
                                    <div className="hub-rank">{i + 1}</div>
                                    <div className="hub-name">{hub.name}</div>
                                </div>
                                <div className="centrality-bar-container">
                                    <div
                                        className="centrality-bar"
                                        style={{
                                            width: `${(hub.betweenness_centrality / maxScore) * 100}%`,
                                        }}
                                    />
                                </div>
                                <div className="hub-score">
                                    {(hub.betweenness_centrality * 100).toFixed(1)}%
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {bridges.length === 0 && hubs.length === 0 && (
                <div className="empty-state">
                    <div className="empty-state-icon">✅</div>
                    <div className="empty-state-title">No Critical Nodes</div>
                    <div className="empty-state-text">
                        No single role acts as a dangerous bridge in the current graph
                    </div>
                </div>
            )}
        </div>
    );
}
