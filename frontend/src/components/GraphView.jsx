import { useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

export default function GraphView() {

  const [graphData, setGraphData] = useState({ nodes: [], links: [] });

  useEffect(() => {
    fetch("http://localhost:8000/graph")
      .then(res => res.json())
      .then(data => setGraphData(data));
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