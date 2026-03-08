import { useState, useCallback } from "react";
import "./App.css";
import GraphView from "./components/GraphView";
import StatsRow from "./components/StatsRow";
import WeakestUserPanel from "./components/WeakestUserPanel";
import CentralityPanel from "./components/CentralityPanel";
import EscalationPanel from "./components/EscalationPanel";
import BlastRadiusPanel from "./components/BlastRadiusPanel";
import AttackSimulationPanel from "./components/AttackSimulationPanel";
import RemediationPanel from "./components/RemediationPanel";
import RoleReassignPanel from "./components/RoleReassignPanel";

const API_BASE = import.meta.env.VITE_API_URL;

function App() {
  const [simData, setSimData] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [blastData, setBlastData] = useState(null);
  const [loadingScan, setLoadingScan] = useState(false);
  const [loadingAws, setLoadingAws] = useState(false);
  const [graphKey, setGraphKey] = useState(0);

  const runSimulation = useCallback(async () => {
    setLoadingScan(true);
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
      setLoadingScan(false);
    }
  }, []);

  const runAwsIngestion = useCallback(async () => {
    setLoadingAws(true);
    try {
      const res = await fetch(`${API_BASE}/ingest-aws`, { method: "POST" });
      if (!res.ok) throw new Error(`Ingest failed: ${res.status}`);
      const data = await res.json();
      setSimData(data);

      // Fetch fresh graph
      const gRes = await fetch(`${API_BASE}/graph`);
      if (gRes.ok) {
        const gData = await gRes.json();
        setGraphData(gData);
        setGraphKey((k) => k + 1);
      }
      setBlastData(null); // Clear previous blast radius
    } catch (err) {
      console.error("AWS Ingestion error:", err);
    } finally {
      setLoadingAws(false);
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

  // Callback when a role is reassigned — refresh graph + panels
  const handleReassigned = useCallback(async (reassignData) => {
    // 1. Refresh graph
    try {
      const gRes = await fetch(`${API_BASE}/graph`);
      if (gRes.ok) {
        const gData = await gRes.json();
        setGraphData(gData);
        setGraphKey((k) => k + 1);
      }
    } catch (err) {
      console.error("Graph refresh failed:", err);
    }

    if (!reassignData || reassignData.status === "expired") {
      return; // Expiration only needs to trigger a graph refresh
    }

    // Update sim data with centrality if available
    if (reassignData.centrality) {
      setSimData((prev) => ({
        ...prev,
        centrality: reassignData.centrality,
      }));
    }

    let targetUser = null;

    // Handle payload from single reassignment endpoint vs batch/temporary
    if (reassignData.user_analysis) {
      // Single endpoint response format
      targetUser = reassignData.user_analysis.user;
      setSimData((prev) => ({
        ...prev,
        weakest_user: reassignData.after?.risk_score > 0 ? {
          user: reassignData.user_analysis.user,
          risk_level: reassignData.after.risk_level,
          overall_risk_score: reassignData.after.risk_score,
          total_escalation_paths: reassignData.after.total_paths,
          max_depth: reassignData.user_analysis.max_depth,
          sensitive_targets: reassignData.user_analysis.sensitive_targets,
        } : prev?.weakest_user,
      }));
    } else if (reassignData.after && typeof reassignData.after === "object") {
      // Batch or temporary endpoint response format (mapping of user -> risk info)
      const users = Object.keys(reassignData.after);
      if (users.length > 0) {
        targetUser = users[0]; // refresh blast radius for at least the first user
      }
    }

    // Refresh blast radius for the reassigned user
    if (targetUser) {
      try {
        const bRes = await fetch(
          `${API_BASE}/blast-radius/${encodeURIComponent(targetUser)}`
        );
        if (bRes.ok) {
          setBlastData(await bRes.json());
        }
      } catch (err) {
        console.error("Blast radius refresh failed:", err);
      }
    }
  }, []);

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
              className={`btn-simulate ${loadingAws ? "loading" : ""}`}
              style={{ background: "rgba(255,153,0,0.15)", border: "1px solid rgba(255,153,0,0.3)", color: "#FF9900" }}
              onClick={runAwsIngestion}
              disabled={loadingAws || loadingScan}
              id="aws-btn"
            >
              {loadingAws ? "⏳" : "☁️"} {loadingAws ? "Fetching…" : "AWS IAM Data"}
            </button>
            <button
              className={`btn-simulate ${loadingScan ? "loading" : ""}`}
              onClick={runSimulation}
              disabled={loadingScan || loadingAws}
              id="simulate-btn"
            >
              {loadingScan ? "⏳" : "⚡"} {loadingScan ? "Scanning…" : "Scan Analysis"}
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
                <div className="legend-item">
                  <span className="legend-dot" style={{background: "#c084fc"}}></span> Policy
                </div>
                <div className="legend-item" style={{marginLeft: "0.5rem", paddingLeft: "1rem", borderLeft: "1px solid rgba(255,255,255,0.1)"}}>
                  <span style={{display: "inline-block", width: "16px", height: "3px", background: "#f43f5e", borderRadius: "2px", boxShadow: "0 0 8px rgba(244, 63, 94, 0.6)"}}></span>
                  <span style={{fontWeight: 600, color: "#f43f5e", letterSpacing: "0.02em"}}>Escalation Chain</span>
                </div>
              </div>
            </div>
            <div className="panel-body no-padding">
              <GraphView graphData={graphData} graphKey={graphKey} />
            </div>
          </div>

          {/* Role Reassignment — full width */}
          <div className="panel panel-full animate-fade-in-up stagger-2">
            <div className="panel-header">
              <div className="panel-title-group">
                <span className="panel-icon">🔄</span>
                <span className="panel-title">What-If Role Reassignment</span>
              </div>
              <span className="panel-badge">sandbox</span>
            </div>
            <div className="panel-body no-padding">
              <RoleReassignPanel
                graphData={graphData}
                onReassigned={handleReassigned}
              />
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

          {/* Attack Simulation — full width */}
          {simData?.weakest_user && (
            <div className="panel panel-full animate-fade-in-up stagger-5">
              <div className="panel-header">
                <div className="panel-title-group">
                  <span className="panel-icon">⚔️</span>
                  <span className="panel-title">
                    Attack Simulation — {simData.weakest_user.user}
                  </span>
                </div>
                <span className="panel-badge">
                  {simData.weakest_user.max_depth} steps
                </span>
              </div>
              <div className="panel-body no-padding panel-scroll">
                <AttackSimulationPanel user={simData.weakest_user.user} />
              </div>
            </div>
          )}

          {/* Remediation — full width */}
          {simData?.weakest_user && (
            <div className="panel panel-full animate-fade-in-up stagger-5">
              <div className="panel-header">
                <div className="panel-title-group">
                  <span className="panel-icon">🛠️</span>
                  <span className="panel-title">
                    Remediation Suggestions — {simData.weakest_user.user}
                  </span>
                </div>
                <span className="risk-badge critical">ACTION REQUIRED</span>
              </div>
              <div className="panel-body no-padding panel-scroll">
                <RemediationPanel user={simData.weakest_user.user} />
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;