import { useState, useCallback } from "react";
import "./App.css";
import GraphView from "./components/GraphView";
import StatsRow from "./components/StatsRow";
import WeakestUserPanel from "./components/WeakestUserPanel";
import CentralityPanel from "./components/CentralityPanel";
import EscalationPanel from "./components/EscalationPanel";
import BlastRadiusPanel from "./components/BlastRadiusPanel";

const API_BASE = import.meta.env.VITE_API_URL;

function App() {
  const [simData, setSimData] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [blastData, setBlastData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [graphKey, setGraphKey] = useState(0);

  const runSimulation = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/simulate`, { method: "POST" });
      if (!res.ok) throw new Error(`Simulate failed: ${res.status}`);
      const data = await res.json();
      setSimData(data);

      // Fetch fresh graph
      const gRes = await fetch(`${API_BASE}/graph`);
      if (gRes.ok) {
        const gData = await gRes.json();
        setGraphData(gData);
        setGraphKey((k) => k + 1);
      }

      // Fetch blast radius for weakest user
      if (data.weakest_user) {
        const bRes = await fetch(
          `${API_BASE}/blast-radius/${encodeURIComponent(data.weakest_user.user)}`
        );
        if (bRes.ok) {
          setBlastData(await bRes.json());
        }
      }
    } catch (err) {
      console.error("Simulation error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load initial graph on mount
  const loadInitialGraph = useCallback(async () => {
    try {
      const gRes = await fetch(`${API_BASE}/graph`);
      if (gRes.ok) {
        const data = await gRes.json();
        setGraphData(data);
      }
    } catch (err) {
      console.error("Initial graph load failed:", err);
    }
  }, []);

  // Run on mount
  useState(() => {
    loadInitialGraph();
  });

  return (
    <div className="app">
      {/* ── Header ──────────────────────────────────── */}
      <header className="header">
        <div className="header-inner">
          <div className="header-brand">
            <div className="header-icon">🛡️</div>
            <div>
              <div className="header-title">Shadow Permission Analyzer</div>
              <div className="header-subtitle">
                IAM Privilege Escalation Detection & Graph Analysis
              </div>
            </div>
          </div>

          <div className="header-actions">
            <div className="header-status">
              <span className="status-dot"></span>
              Neo4j Connected
            </div>
            <button
              className={`btn-simulate ${loading ? "loading" : ""}`}
              onClick={runSimulation}
              disabled={loading}
              id="simulate-btn"
            >
              {loading ? "⏳" : "⚡"}{" "}
              {loading ? "Analyzing…" : "Run Simulation"}
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Content ───────────────────────────── */}
      <main className="main-content">
        {/* Stats Row */}
        <StatsRow simData={simData} graphData={graphData} />

        {/* Dashboard Grid */}
        <div className="dashboard-grid">
          {/* Graph Panel — full width */}
          <div className="panel panel-full animate-fade-in-up stagger-1">
            <div className="panel-header">
              <div className="panel-title-group">
                <span className="panel-icon">🔗</span>
                <span className="panel-title">
                  IAM Permission Graph
                </span>
              </div>
              <div className="graph-legend">
                <div className="legend-item">
                  <span className="legend-dot user"></span> User
                </div>
                <div className="legend-item">
                  <span className="legend-dot role"></span> Role
                </div>
                <div className="legend-item">
                  <span className="legend-dot resource"></span> Resource
                </div>
              </div>
            </div>
            <div className="panel-body no-padding">
              <GraphView graphData={graphData} graphKey={graphKey} />
            </div>
          </div>

          {/* Weakest User + Centrality Hubs */}
          <div className="panel animate-fade-in-up stagger-2">
            <div className="panel-header">
              <div className="panel-title-group">
                <span className="panel-icon">⚠️</span>
                <span className="panel-title">Weakest User</span>
              </div>
              {simData?.weakest_user && (
                <span className={`risk-badge ${simData.weakest_user.risk_level.toLowerCase()}`}>
                  {simData.weakest_user.risk_level}
                </span>
              )}
            </div>
            <div className="panel-body">
              <WeakestUserPanel data={simData?.weakest_user} />
            </div>
          </div>

          <div className="panel animate-fade-in-up stagger-3">
            <div className="panel-header">
              <div className="panel-title-group">
                <span className="panel-icon">🎯</span>
                <span className="panel-title">Critical Nodes</span>
              </div>
              {simData?.centrality && (
                <span className="panel-badge">
                  {simData.centrality.total_bridges || 0} bridge{simData.centrality.total_bridges !== 1 ? "s" : ""} · {simData.centrality.total_hubs} hub{simData.centrality.total_hubs !== 1 ? "s" : ""}
                </span>
              )}
            </div>
            <div className="panel-body panel-scroll">
              <CentralityPanel data={simData?.centrality} />
            </div>
          </div>

          {/* Escalation Paths — full width */}
          <div className="panel panel-full animate-fade-in-up stagger-4">
            <div className="panel-header">
              <div className="panel-title-group">
                <span className="panel-icon">📈</span>
                <span className="panel-title">
                  Escalation Analysis by User
                </span>
              </div>
              {simData?.user_analyses && (
                <span className="panel-badge">
                  {simData.user_analyses.length} users analyzed
                </span>
              )}
            </div>
            <div className="panel-body no-padding panel-scroll">
              <EscalationPanel data={simData?.user_analyses} />
            </div>
          </div>

          {/* Blast Radius — full width */}
          {blastData &&
            blastData.total_affected_resources > 0 && (
              <div className="panel panel-full animate-fade-in-up stagger-5">
                <div className="panel-header">
                  <div className="panel-title-group">
                    <span className="panel-icon">💥</span>
                    <span className="panel-title">
                      Blast Radius — {blastData.user}
                    </span>
                  </div>
                  <span
                    className={`risk-badge ${blastData.risk_level.toLowerCase()}`}
                  >
                    {blastData.risk_level}
                  </span>
                </div>
                <div className="panel-body no-padding panel-scroll">
                  <BlastRadiusPanel data={blastData} />
                </div>
              </div>
            )}
        </div>
      </main>
    </div>
  );
}

export default App;