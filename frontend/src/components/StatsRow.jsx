export default function StatsRow({ simData, graphData }) {
    const ds = simData?.dataset_summary;
    const nodes = graphData?.nodes?.length || 0;
    const links = graphData?.links?.length || 0;

    const numRoles = graphData?.nodes?.filter(n => n.label === "Role").length;
    const numResources = graphData?.nodes?.filter(n => n.label === "Resource").length;

    const stats = [
        { label: "Users", value: ds?.users ?? "—", color: "indigo" },
        { label: "Roles", value: numRoles ?? ds?.roles ?? "—", color: "emerald" },
        { label: "Resources", value: numResources ?? ds?.resources ?? "—", color: "amber" },
        { label: "Graph Nodes", value: nodes ?? "—", color: "cyan" },
        { label: "Graph Edges", value: links ?? "—", color: "purple" },
        {
            label: "Risk Score",
            value: simData?.weakest_user?.overall_risk_score ?? "—",
            color: "rose",
        },
    ];

    return (
        <div className="stats-row">
            {stats.map((s, i) => (
                <div
                    key={s.label}
                    className={`stat-card stagger-${i + 1}`}
                >
                    <div className="stat-label">{s.label}</div>
                    <div className={`stat-value ${s.color}`}>{s.value}</div>
                </div>
            ))}
        </div>
    );
}
