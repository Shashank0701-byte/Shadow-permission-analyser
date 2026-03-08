import { useState, useCallback, useRef, useEffect } from "react";
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
  const weakestUserRef = useRef(null);

  const runSimulation = useCallback(async () => {
    setLoadingScan(true);
    try {
      const res = await fetch(`${API_BASE}/simulate`, { method: "POST" });
      if (!res.ok) throw new Error(`Simulate failed: ${res.status}`);
      const data = await res.json();
      setSimData(data);
      if (data.weakest_user?.user) {
        weakestUserRef.current = data.weakest_user.user;
      } else {
        weakestUserRef.current = null;
        setBlastData(null);
      }

      const userParams = weakestUserRef.current ? `?highlight_user=${encodeURIComponent(weakestUserRef.current)}` : "";

      // Fetch fresh graph
      const gRes = await fetch(`${API_BASE}/graph${userParams}`);
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
      if (data.weakest_user?.user) {
        weakestUserRef.current = data.weakest_user.user;
      } else {
        weakestUserRef.current = "";
        setBlastData(null);
      }

      const userParams = weakestUserRef.current ? `?highlight_user=${encodeURIComponent(weakestUserRef.current)}` : "";

      // Fetch fresh graph
      const gRes = await fetch(`${API_BASE}/graph${userParams}`);
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
      const userParams = weakestUserRef.current ? `?highlight_user=${encodeURIComponent(weakestUserRef.current)}` : "";
      const gRes = await fetch(`${API_BASE}/graph${userParams}`);
      if (gRes.ok) {
        const data = await gRes.json();
        setGraphData(data);
      }
    } catch (err) {
      console.error("Initial graph load failed:", err);
    }
  }, []);

  // Run on mount
  useEffect(() => {
    loadInitialGraph();
  }, [loadInitialGraph]);

  // Callback when a role is reassigned — refresh graph + panels
  const handleReassigned = useCallback(async (reassignData) => {
    if (!reassignData || reassignData.status === "expired") {
      try {
        const userParams = weakestUserRef.current ? `?highlight_user=${encodeURIComponent(weakestUserRef.current)}` : "";
        const gRes = await fetch(`${API_BASE}/graph${userParams}`);
        if (gRes.ok) {
          const gData = await gRes.json();
          setGraphData(gData);
          setGraphKey((k) => k + 1);
        }
      } catch (err) {
        console.error("Graph refresh failed:", err);
      }
      return;
    }

    if (!simData) return;
    const newSimData = { ...simData };

    // 1. Update centrality
    if (reassignData.centrality) {
      newSimData.centrality = reassignData.centrality;
    }

    // 2. Update user_analyses and determine weakest user
    newSimData.user_analyses = [...(simData.user_analyses || [])];

    if (reassignData.user_analysis) {
      const ua = reassignData.user_analysis;
      const existingIdx = newSimData.user_analyses.findIndex((u) => u.user === ua.user);
      if (existingIdx !== undefined && existingIdx >= 0) {
        newSimData.user_analyses[existingIdx] = ua;
      } else {
        newSimData.user_analyses.push(ua);
      }
    } else if (reassignData.after && typeof reassignData.after === "object") {
      const users = Object.keys(reassignData.after);
      if (users.length > 0) {
        users.forEach(u => {
           const afterStats = reassignData.after[u];
           const existingIdx = newSimData.user_analyses.findIndex(ua => ua.user === u);
           if (existingIdx !== undefined && existingIdx >= 0) {
              newSimData.user_analyses[existingIdx] = {
                 ...newSimData.user_analyses[existingIdx],
                 overall_risk_score: afterStats.risk_score,
                 risk_level: afterStats.risk_level,
                 total_paths: afterStats.total_paths
              };
           }
        });
      }
    }

    if (newSimData.user_analyses && newSimData.user_analyses.length > 0) {
      const weakest = [...newSimData.user_analyses].sort((a, b) => (b.overall_risk_score || 0) - (a.overall_risk_score || 0))[0];
      if (weakest && weakest.overall_risk_score > 0) {
        newSimData.weakest_user = {
          user: weakest.user,
          risk_level: weakest.risk_level,
          overall_risk_score: weakest.overall_risk_score,
          total_escalation_paths: weakest.total_paths,
          max_depth: weakest.max_depth,
          sensitive_targets: weakest.sensitive_targets,
        };
      } else {
        newSimData.weakest_user = null;
      }
    }

    const nextWeakestUser = newSimData.weakest_user?.user ?? null;
    weakestUserRef.current = nextWeakestUser;
    
    setSimData(newSimData);

    try {
      const userParams = weakestUserRef.current ? `?highlight_user=${encodeURIComponent(weakestUserRef.current)}` : "";
      const gRes = await fetch(`${API_BASE}/graph${userParams}`);
      if (gRes.ok) {
        const gData = await gRes.json();
        setGraphData(gData);
        setGraphKey((k) => k + 1);
      }
    } catch (err) {
      console.error("Graph refresh failed:", err);
    }

    if (nextWeakestUser) {
      try {
        const bRes = await fetch(
          `${API_BASE}/blast-radius/${encodeURIComponent(nextWeakestUser)}`
        );
        if (bRes.ok) {
          setBlastData(await bRes.json());
        }
      } catch (err) {
        console.error("Blast radius refresh failed:", err);
      }
    } else {
      setBlastData(null);
    }
  }, [simData]);

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
            {/* <div className="header-status">
              <span className="status-dot"></span>
              Neo4j Connected
            </div> */}
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
                  <span className="legend-dot" style={{ background: "#c084fc" }}></span> Policy
                </div>
                <div className="legend-item" style={{ marginLeft: "0.5rem", paddingLeft: "1rem", borderLeft: "1px solid rgba(255,255,255,0.1)" }}>
                  <span style={{ display: "inline-block", width: "16px", height: "3px", background: "#f43f5e", borderRadius: "2px", boxShadow: "0 0 8px rgba(244, 63, 94, 0.6)" }}></span>
                  <span style={{ fontWeight: 600, color: "#f43f5e", letterSpacing: "0.02em" }}>Escalation Chain</span>
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