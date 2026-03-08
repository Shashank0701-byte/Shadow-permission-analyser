import { useState, useEffect, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_URL;

export default function RoleReassignPanel({ graphData, onReassigned }) {
  const [selectedUser, setSelectedUser] = useState("");
  const [oldRole, setOldRole] = useState("");
  const [newRole, setNewRole] = useState("");
  const [duration, setDuration] = useState("0"); // 0 = permanent
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeSessions, setActiveSessions] = useState([]);
  
  const sessionsRef = useRef(0);

  const users = (graphData?.nodes || [])
    .filter((n) => n.label === "User")
    .map((n) => n.name);
  const roles = (graphData?.nodes || [])
    .filter((n) => n.label === "Role")
    .map((n) => n.name);

  // Poll for active temporary sessions
  useEffect(() => {
    let timeout;
    const fetchSessions = async () => {
      try {
        const res = await fetch(`${API_BASE}/temporary-sessions`);
        if (res.ok) {
          const data = await res.json();
          // If a session just expired (count went down), trigger a graph refresh
          if (sessionsRef.current > data.sessions.length && onReassigned) {
             onReassigned({ status: "expired" }); // tell parent to refresh graph
          }
          sessionsRef.current = data.sessions.length;
          setActiveSessions(data.sessions);
        }
      } catch (err) {
        // ignore polling errors
      }
      timeout = setTimeout(fetchSessions, 2000);
    };
    fetchSessions();
    return () => clearTimeout(timeout);
  }, [onReassigned]);

  // Add current selection to the queue (permanent only for batch)
  const handleAdd = () => {
    if (!selectedUser || !newRole) return;
    setQueue((prev) => [
      ...prev,
      { user: selectedUser, old_role: oldRole || null, new_role: newRole, id: Date.now() },
    ]);
    setSelectedUser("");
    setOldRole("");
    setNewRole("");
    setDuration("0");
  };

  const handleRemove = (id) => {
    setQueue((prev) => prev.filter((c) => c.id !== id));
  };

  // Apply a single change immediately
  const handleApplySingle = async () => {
    if (!selectedUser || !newRole) return;
    setLoading(true);
    setResult(null);
    try {
      let data;
      if (duration === "0") {
        // Permanent
        const params = new URLSearchParams({ user: selectedUser, new_role: newRole });
        if (oldRole) params.set("old_role", oldRole);
        const res = await fetch(`${API_BASE}/reassign-role?${params}`, { method: "POST" });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Failed: ${res.status}`);
        }
        data = await res.json();
      } else {
        // Temporary
        const body = {
          user: selectedUser,
          old_role: oldRole || null,
          new_role: newRole,
          duration_seconds: parseInt(duration),
        };
        const res = await fetch(`${API_BASE}/temporary-access`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Failed: ${res.status}`);
        }
        data = await res.json();
      }

      if (data.after && !data.user_analysis && typeof data.after === "object") {
        setResult({ batch: data, isTemp: duration !== "0" });
      } else {
        setResult({ single: data, isTemp: duration !== "0" });
      }
      setSelectedUser("");
      setOldRole("");
      setNewRole("");
      setDuration("0");
      if (onReassigned) onReassigned(data);
      
      // Force immediate session fetch
      fetch(`${API_BASE}/temporary-sessions`).then(r => r.json()).then(d => {
         setActiveSessions(d.sessions);
         sessionsRef.current = d.sessions.length;
      }).catch(()=>{});

    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  // Apply all queued changes in batch
  const handleApplyAll = async () => {
    if (!queue.length) return;
    setLoading(true);
    setResult(null);
    try {
      const body = {
        changes: queue.map((c) => ({ user: c.user, old_role: c.old_role, new_role: c.new_role })),
      };
      const res = await fetch(`${API_BASE}/reassign-roles-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Batch failed: ${res.status}`);
      }
      const data = await res.json();
      setResult({ batch: data });
      setQueue([]);
      if (onReassigned) onReassigned(data);
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  if (!users.length || !roles.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🔄</div>
        <div className="empty-title">No Graph Data</div>
        <div className="empty-desc">Load AWS data first to enable role reassignment.</div>
      </div>
    );
  }

  return (
    <div style={{ padding: "1rem" }}>
      {/* Controls Row */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1.2fr 1fr 1fr 0.8fr auto auto",
        gap: "0.5rem",
        alignItems: "end",
        marginBottom: "0.75rem",
      }}>
        <div>
          <label style={labelStyle}>Select User</label>
          <select style={selectStyle} value={selectedUser} onChange={(e) => setSelectedUser(e.target.value)}>
            <option value="">— Pick user —</option>
            {users.map((u) => (<option key={u} value={u}>{u}</option>))}
          </select>
        </div>
        <div>
          <label style={labelStyle}>Current Role <span style={{ opacity: 0.4 }}>(optional)</span></label>
          <select style={selectStyle} value={oldRole} onChange={(e) => setOldRole(e.target.value)}>
            <option value="">— None —</option>
            {roles.map((r) => (<option key={r} value={r}>{r}</option>))}
          </select>
        </div>
        <div>
          <label style={labelStyle}>Assign to Role</label>
          <select
            style={{ ...selectStyle, borderColor: newRole ? "rgba(52, 211, 153, 0.4)" : selectStyle.borderColor }}
            value={newRole}
            onChange={(e) => setNewRole(e.target.value)}
          >
            <option value="">— Pick role —</option>
            {roles.map((r) => (<option key={r} value={r}>{r}</option>))}
          </select>
        </div>
        <div>
          <label style={labelStyle}>Duration</label>
          <select style={selectStyle} value={duration} onChange={(e) => setDuration(e.target.value)}>
            <option value="0">Permanent</option>
            <option value="30">30 Seconds (Demo)</option>
            <option value="60">1 Minute</option>
            <option value="300">5 Minutes</option>
          </select>
        </div>

        {/* Apply single change immediately */}
        <button
          onClick={handleApplySingle}
          disabled={loading || !selectedUser || !newRole}
          style={applyBtnStyle(loading || !selectedUser || !newRole, duration !== "0")}
        >
          {loading && !queue.length ? "⏳ Applying…" : duration !== "0" ? "⏱️ Temporary Elevate" : "🔄 Apply & Rescan"}
        </button>

        {/* Queue for batch (only permanent allowed in batch for now) */}
        <button
          onClick={handleAdd}
          disabled={!selectedUser || !newRole || duration !== "0"}
          title={duration !== "0" ? "Temporary access cannot be batched" : ""}
          style={addBtnStyle(!selectedUser || !newRole || duration !== "0")}
        >
          + Add
        </button>
      </div>

      {/* Active Temporary Sessions */}
      {activeSessions.length > 0 && (
        <div style={{
          marginBottom: "0.75rem",
          borderRadius: "0.5rem",
          border: "1px solid rgba(251, 191, 36, 0.3)",
          background: "rgba(251, 191, 36, 0.05)",
          overflow: "hidden",
        }}>
          <div style={{
            padding: "0.4rem 0.75rem",
            fontSize: "0.55rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#fbbf24",
            borderBottom: "1px solid rgba(251, 191, 36, 0.1)",
            display: "flex",
            justifyContent: "space-between"
          }}>
            <span>⏳ Active Time-Bound Sessions ({activeSessions.length})</span>
            <span style={{ opacity: 0.7 }}>Auto-Rollback Enabled</span>
          </div>
          {activeSessions.map((session, idx) => (
            <div key={idx} style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "0.5rem 0.75rem",
              borderBottom: "1px solid rgba(255,255,255,0.04)",
              fontSize: "0.72rem",
            }}>
              <div>
                <span style={{ color: "#60a5fa", fontWeight: 700 }}>{session.user}</span>
                <span style={{ color: "rgba(255,255,255,0.3)", margin: "0 0.4rem" }}>has temporary access to</span>
                <span style={{ color: "#34d399", fontWeight: 700, padding: "0.1rem 0.3rem", background: "rgba(52,211,153,0.1)", borderRadius: "3px" }}>{session.new_role}</span>
              </div>
              <div style={{ color: "#fbbf24", fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: "0.8rem", background: "rgba(251, 191, 36, 0.1)", padding: "0.2rem 0.4rem", borderRadius: "4px" }}>
                <Countdown expiresAt={session.expires_at} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pending Queue for Batch */}
      {queue.length > 0 && (
        <div style={{
          marginBottom: "0.75rem",
          borderRadius: "0.5rem",
          border: "1px solid rgba(96, 165, 250, 0.15)",
          background: "rgba(96, 165, 250, 0.04)",
          overflow: "hidden",
        }}>
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "0.4rem 0.75rem",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
          }}>
            <span style={{ fontSize: "0.55rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>
              Queued Permanent Changes ({queue.length})
            </span>
            <button
              onClick={handleApplyAll}
              disabled={loading}
              style={{
                ...applyBtnStyle(loading, false),
                padding: "0.3rem 0.8rem",
                fontSize: "0.65rem",
              }}
            >
              {loading ? "⏳ Applying…" : `🔄 Apply All (${queue.length})`}
            </button>
          </div>
          {queue.map((c) => (
            <div key={c.id} style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "0.45rem 0.75rem",
              borderBottom: "1px solid rgba(255,255,255,0.04)",
              fontSize: "0.72rem",
            }}>
              <div>
                <span style={{ color: "#60a5fa", fontWeight: 700 }}>{c.user}</span>
                <span style={{ color: "rgba(255,255,255,0.3)", margin: "0 0.4rem" }}>→</span>
                {c.old_role && (
                  <>
                    <span style={{ color: "#f43f5e", textDecoration: "line-through", opacity: 0.7 }}>{c.old_role}</span>
                    <span style={{ color: "rgba(255,255,255,0.3)", margin: "0 0.3rem" }}>→</span>
                  </>
                )}
                <span style={{ color: "#34d399", fontWeight: 700 }}>{c.new_role}</span>
              </div>
              <button onClick={() => handleRemove(c.id)} style={removeBtnStyle}>✕</button>
            </div>
          ))}
        </div>
      )}

      {/* Single Result */}
      {result?.single && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr",
          gap: "0.75rem",
          alignItems: "center",
          marginBottom: "0.5rem",
        }}>
          <div style={comparisonCardStyle}>
            <div style={compLabelStyle}>BEFORE</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 800, color: getRiskColor(result.single.before.risk_level), fontFamily: "'JetBrains Mono', monospace" }}>
              {result.single.before.risk_score}
            </div>
            <div style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.4)" }}>
              {result.single.before.risk_level} · {result.single.before.total_paths} path{result.single.before.total_paths !== 1 ? "s" : ""}
            </div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "1.5rem", color: result.single.risk_increased ? "#f43f5e" : result.single.risk_delta === 0 ? "#fbbf24" : "#34d399" }}>
              {result.single.risk_increased ? "⬆️" : result.single.risk_delta === 0 ? "➡️" : "⬇️"}
            </div>
            <div style={{ fontSize: "0.8rem", fontWeight: 800, fontFamily: "'JetBrains Mono', monospace", color: result.single.risk_increased ? "#f43f5e" : "#34d399" }}>
              {result.single.risk_delta > 0 ? "+" : ""}{result.single.risk_delta}
            </div>
            {result.isTemp && (
              <div style={{ marginTop: "0.3rem", fontSize: "0.55rem", background: "rgba(251,191,36,0.1)", color: "#fbbf24", padding: "0.15rem 0.4rem", borderRadius: "1rem", fontWeight: 700 }}>
                TEMP ELEVATED
              </div>
            )}
          </div>
          <div style={comparisonCardStyle}>
            <div style={compLabelStyle}>AFTER</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 800, color: getRiskColor(result.single.after.risk_level), fontFamily: "'JetBrains Mono', monospace" }}>
              {result.single.after.risk_score}
            </div>
            <div style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.4)" }}>
              {result.single.after.risk_level} · {result.single.after.total_paths} path{result.single.after.total_paths !== 1 ? "s" : ""}
            </div>
          </div>
        </div>
      )}

      {/* Batch Result map (unchanged) */}
    </div>
  );
}

// Countdown Helper Component
function Countdown({ expiresAt }) {
  const [timeLeft, setTimeLeft] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      const exp = new Date(expiresAt);
      const diff = Math.floor((exp - now) / 1000);
      
      if (diff <= 0) {
        setTimeLeft("00:00");
      } else {
        const m = Math.floor(diff / 60).toString().padStart(2, "0");
        const s = (diff % 60).toString().padStart(2, "0");
        setTimeLeft(`${m}:${s}`);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [expiresAt]);

  return <span>{timeLeft || "..."}</span>;
}

// ── Styles ──

const labelStyle = {
  display: "block", fontSize: "0.6rem", fontWeight: 700,
  letterSpacing: "0.08em", textTransform: "uppercase",
  color: "rgba(255,255,255,0.45)", marginBottom: "0.35rem",
};

const selectStyle = {
  width: "100%", padding: "0.5rem 0.6rem", borderRadius: "0.5rem",
  border: "1px solid rgba(255,255,255,0.1)", background: "#1a1a2e",
  color: "rgba(255,255,255,0.9)", fontSize: "0.72rem", fontWeight: 600,
  appearance: "auto", cursor: "pointer", outline: "none", colorScheme: "dark",
};

const applyBtnStyle = (disabled, isTemp = false) => ({
  padding: "0.55rem 0.8rem", borderRadius: "0.5rem",
  border: `1px solid ${isTemp ? "rgba(251, 191, 36, 0.3)" : "rgba(96,165,250,0.3)"}`,
  background: disabled
    ? (isTemp ? "rgba(251, 191, 36, 0.03)" : "rgba(96,165,250,0.03)")
    : (isTemp ? "rgba(251, 191, 36, 0.15)" : "rgba(96,165,250,0.15)"),
  color: isTemp ? "#fbbf24" : "#60a5fa", fontWeight: 700, fontSize: "0.72rem",
  cursor: disabled ? "not-allowed" : "pointer",
  opacity: disabled ? 0.4 : 1, transition: "all 0.2s", whiteSpace: "nowrap",
});

const addBtnStyle = (disabled) => ({
  padding: "0.55rem 1rem", borderRadius: "0.5rem",
  border: "1px solid rgba(52,211,153,0.3)",
  background: disabled ? "rgba(52,211,153,0.03)" : "rgba(52,211,153,0.12)",
  color: "#34d399", fontWeight: 700, fontSize: "0.72rem",
  cursor: disabled ? "not-allowed" : "pointer",
  opacity: disabled ? 0.4 : 1, transition: "all 0.2s", whiteSpace: "nowrap",
});

const removeBtnStyle = {
  background: "transparent", border: "none", color: "#f43f5e",
  cursor: "pointer", fontSize: "0.65rem", fontWeight: 700, opacity: 0.7,
  padding: "0.15rem 0.4rem", borderRadius: "0.25rem",
};

const comparisonCardStyle = {
  background: "rgba(255,255,255,0.03)", borderRadius: "0.75rem",
  border: "1px solid rgba(255,255,255,0.06)", padding: "0.65rem",
  textAlign: "center",
};

const compLabelStyle = {
  fontSize: "0.55rem", fontWeight: 700, letterSpacing: "0.1em",
  color: "rgba(255,255,255,0.35)", marginBottom: "0.3rem",
};

function getRiskColor(level) {
  switch (level) {
    case "CRITICAL": return "#f43f5e";
    case "HIGH": return "#fb923c";
    case "MEDIUM": return "#fbbf24";
    default: return "#34d399";
  }
}
