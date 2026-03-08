"""Centrality analysis for the IAM permission graph.

Answers the question: **"Which node is the weak link?"**

Two complementary analyses:

1. **Betweenness centrality** — roles that sit on the most shortest-paths
   between users and resources (high-traffic privilege hubs).
2. **Critical bridges** — roles that, if removed, would *break* at least
   one escalation path.  These are the exact nodes "where it goes wrong."

Public API
----------
``find_critical_hubs()``
    Returns centrality scores, privilege hubs, and critical bridge nodes.
"""

import networkx as nx

from app.graph.queries import get_full_graph


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_networkx_graph() -> nx.DiGraph:
    """Fetch the full IAM graph from Neo4j and return a NetworkX DiGraph."""
    data = get_full_graph()
    G = nx.DiGraph()

    for node in data["nodes"]:
        G.add_node(
            node["id"],
            name=node["name"],
            label=node["label"],
            sensitivity=node.get("sensitivity"),
        )

    for link in data["links"]:
        G.add_edge(
            link["source"],
            link["target"],
            type=link["type"],
        )

    return G


# ---------------------------------------------------------------------------
# Critical bridge detection
# ---------------------------------------------------------------------------

def _find_bridge_roles(G: nx.DiGraph) -> list[dict]:
    """Find Role nodes that are critical bridges in escalation paths.

    A role is a "bridge" if removing it would disconnect at least one
    User from a Resource they could previously reach.  These are the
    exact nodes where the security design goes wrong.
    """
    # Collect all User and Resource node ids
    users = [n for n, d in G.nodes(data=True) if d.get("label") == "User"]
    resources = [n for n, d in G.nodes(data=True) if d.get("label") == "Resource"]
    roles = [n for n, d in G.nodes(data=True) if d.get("label") == "Role"]

    if not users or not resources or not roles:
        return []

    # Count how many (user → resource) pairs are reachable in the full graph
    def count_reachable_pairs(graph):
        count = 0
        pairs = []
        for u in users:
            if u not in graph:
                continue
            for r in resources:
                if r not in graph:
                    continue
                if nx.has_path(graph, u, r):
                    count += 1
                    pairs.append((u, r))
        return count, pairs

    base_count, base_pairs = count_reachable_pairs(G)

    if base_count == 0:
        return []

    bridges = []
    for role_id in roles:
        # Temporarily remove this role node
        H = G.copy()
        H.remove_node(role_id)
        new_count, _ = count_reachable_pairs(H)

        broken = base_count - new_count
        if broken > 0:
            attrs = G.nodes[role_id]
            # Find which specific pairs are broken
            broken_pairs = []
            for u, r in base_pairs:
                if u in H and r in H and not nx.has_path(H, u, r):
                    broken_pairs.append({
                        "user": G.nodes[u].get("name"),
                        "resource": G.nodes[r].get("name"),
                    })

            bridges.append({
                "id": role_id,
                "name": attrs.get("name"),
                "label": "Role",
                "paths_broken": broken,
                "broken_connections": broken_pairs,
                "impact": round(broken / base_count * 100, 1),
            })

    # Sort by number of paths broken (most impactful first)
    bridges.sort(key=lambda b: b["paths_broken"], reverse=True)
    return bridges


# ---------------------------------------------------------------------------
# Centrality computation
# ---------------------------------------------------------------------------

def find_critical_hubs(hub_threshold: float = 0.1) -> dict:
    """Compute centrality, find privilege hubs, and identify bridge nodes.

    Returns
    -------
    dict
        ``all_centrality``
            Centrality scores for every node, sorted descending.
        ``critical_hubs``
            Role nodes with high betweenness centrality.
        ``critical_bridges``
            Role nodes whose removal breaks escalation paths.
        ``hub_threshold``
            The threshold that was applied.
        ``total_nodes`` / ``total_hubs`` / ``total_bridges``
            Counts.
    """
    G = _build_networkx_graph()

    if G.number_of_nodes() == 0:
        return {
            "all_centrality": [],
            "critical_hubs": [],
            "critical_bridges": [],
            "hub_threshold": hub_threshold,
            "total_nodes": 0,
            "total_hubs": 0,
            "total_bridges": 0,
        }

    # ── Betweenness centrality ──────────────────────────────────────
    bc = nx.betweenness_centrality(G, normalized=True)

    all_centrality = []
    for node_id, score in sorted(bc.items(), key=lambda x: x[1], reverse=True):
        attrs = G.nodes[node_id]
        all_centrality.append({
            "id": node_id,
            "name": attrs.get("name"),
            "label": attrs.get("label"),
            "betweenness_centrality": round(score, 6),
        })

    # Adaptive threshold: use the provided value, but if it yields
    # zero hubs, fall back to "top roles by centrality" so we always
    # surface something useful for small graphs.
    role_entries = [e for e in all_centrality if e["label"] == "Role"]
    critical_hubs = [
        e for e in role_entries
        if e["betweenness_centrality"] >= hub_threshold
    ]

    # Fallback: if no hubs found, take all roles with centrality > 0
    if not critical_hubs:
        critical_hubs = [
            e for e in role_entries
            if e["betweenness_centrality"] > 0
        ]

    # ── Critical bridges ────────────────────────────────────────────
    critical_bridges = _find_bridge_roles(G)

    return {
        "all_centrality": all_centrality,
        "critical_hubs": critical_hubs,
        "critical_bridges": critical_bridges,
        "hub_threshold": hub_threshold,
        "total_nodes": G.number_of_nodes(),
        "total_hubs": len(critical_hubs),
        "total_bridges": len(critical_bridges),
    }
