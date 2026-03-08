import ForceGraph2D from "react-force-graph-2d";
import { useRef, useCallback } from "react";

const NODE_COLORS = {
  User: "#60a5fa",
  Role: "#34d399",
  Resource: "#fbbf24",
  Policy: "#c084fc",
};

const EDGE_COLORS = {
  ASSIGNED: "rgba(96, 165, 250, 0.35)",
  ASSUME: "rgba(52, 211, 153, 0.35)",
  ACCESS: "rgba(251, 191, 36, 0.35)",
  HAS_ROLE: "rgba(96, 165, 250, 0.35)",
  HAS_POLICY: "rgba(192, 132, 252, 0.35)",
};

const hexToRgba = (hex, alpha) => {
  if (!hex.startsWith('#')) return hex;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

export default function GraphView({ graphData, graphKey }) {
  const fgRef = useRef();

  const paintNode = useCallback((node, ctx) => {
    const color = NODE_COLORS[node.label] || "#64748b";
    const size = node.label === "Resource" || node.label === "Policy" ? 7 : node.label === "Role" ? 6 : 5;

    // Outer glow
    ctx.beginPath();
    ctx.arc(node.x, node.y, size + 3, 0, 2 * Math.PI);
    ctx.fillStyle = hexToRgba(color, 0.15);
    ctx.fill();

    // Node circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Border
    ctx.strokeStyle = "rgba(255,255,255,0.2)";
    ctx.lineWidth = 0.5;
    ctx.stroke();

    // Label
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "bold 3.5px Inter, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(node.name || "", node.x + size + 3, node.y + 1.5);
  }, []);

  const paintLink = useCallback((link, ctx) => {
    // If it's an escalation edge, glow with a danger color
    if (link.is_escalation) {
      ctx.strokeStyle = "rgba(244, 63, 94, 0.85)";
      ctx.lineWidth = 2.5;
    } else {
      ctx.strokeStyle = EDGE_COLORS[link.type] || "rgba(100,100,100,0.2)";
      ctx.lineWidth = 1.2;
    }
    ctx.beginPath();
    ctx.moveTo(link.source.x, link.source.y);
    ctx.lineTo(link.target.x, link.target.y);
    ctx.stroke();
  }, []);

  return (
    <div className="graph-container">
      <ForceGraph2D
        key={graphKey}
        ref={fgRef}
        graphData={graphData}
        nodeLabel="name"
        nodeCanvasObject={paintNode}
        linkCanvasObject={paintLink}
        backgroundColor="transparent"
        width={undefined}
        height={420}
        cooldownTicks={80}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={0.85}
        linkDirectionalArrowColor={() => "rgba(148, 163, 184, 0.4)"}
        onEngineStop={() => fgRef.current?.zoomToFit(300, 40)}
      />
    </div>
  );
}