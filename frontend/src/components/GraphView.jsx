import { useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

export default function GraphView() {

  const [graphData, setGraphData] = useState({ nodes: [], links: [] });

  const API_BASE = import.meta.env.VITE_API_URL;

useEffect(() => {
  const loadGraph = async () => {
    try {
      const res = await fetch(`${API_BASE}/graph`);

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const data = await res.json();
      setGraphData(data);

    } catch (err) {
      console.error("Graph fetch failed:", err);
    }
  };

  loadGraph();
}, []);

  const nodeColor = (node) => {
    if (node.label === "User") return "#1f77b4";
    if (node.label === "Role") return "#2ca02c";
    if (node.label === "Resource") return "#ff7f0e";
    return "#999";
  };

  return (
    <ForceGraph2D
      graphData={graphData}
      nodeLabel="name"
      nodeAutoColorBy="label"
      nodeCanvasObject={(node, ctx) => {
        ctx.fillStyle = nodeColor(node);
        ctx.beginPath();
        ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI);
        ctx.fill();

        ctx.fillStyle = "black";
        ctx.font = "10px Arial";
        ctx.fillText(node.name, node.x + 8, node.y + 3);
      }}
    />
  );
}