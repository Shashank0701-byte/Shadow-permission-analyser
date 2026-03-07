"""Centrality analysis for the IAM permission graph.

Builds a NetworkX directed graph from the Neo4j data and computes
**betweenness centrality** to identify roles that appear frequently on
the shortest paths between users and resources.  These roles act as
*critical privilege hubs* — compromising or misconfiguring them has an
outsized impact on overall access control.

Public API
----------
``find_critical_hubs()``
    Returns betweenness centrality scores for every node and highlights
    Role nodes that exceed a configurable hub threshold.
"""

import networkx as nx

from app.graph.queries import get_full_graph


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_networkx_graph() -> nx.DiGraph:
    """Fetch the full IAM graph from Neo4j and return a NetworkX DiGraph.

    Each node carries ``label`` (User / Role / Resource) and ``name``
    attributes.  Each edge carries a ``type`` attribute (ASSIGNED /
    ASSUME / ACCESS).
    """
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
# Centrality computation
# ---------------------------------------------------------------------------

def find_critical_hubs(hub_threshold: float = 0.1) -> dict:
    """Compute betweenness centrality and identify critical privilege hubs.

    Parameters
    ----------
    hub_threshold : float
        Nodes whose betweenness centrality is **>= hub_threshold** are
        flagged as critical hubs.  Default is **0.1** (top 10 %% of the
        theoretical maximum, which is 1.0 for a normalised score).

    Returns
    -------
    dict
        ``all_centrality``
            Centrality scores for every node, sorted descending.
        ``critical_hubs``
            Subset filtered to Role nodes above the threshold.
        ``hub_threshold``
            The threshold that was applied.
        ``total_nodes``
            Total node count in the graph.
        ``total_hubs``
            Number of critical hubs found.
    """
    G = _build_networkx_graph()

    if G.number_of_nodes() == 0:
        return {
            "all_centrality": [],
            "critical_hubs": [],
            "hub_threshold": hub_threshold,
            "total_nodes": 0,
            "total_hubs": 0,
        }

    # Betweenness centrality (normalised to 0-1)
    bc = nx.betweenness_centrality(G, normalized=True)

    # Build a sorted list of all node scores
    all_centrality = []
    for node_id, score in sorted(bc.items(), key=lambda x: x[1], reverse=True):
        attrs = G.nodes[node_id]
        all_centrality.append({
            "id": node_id,
            "name": attrs.get("name"),
            "label": attrs.get("label"),
            "betweenness_centrality": round(score, 6),
        })

    # Critical hubs - only Role nodes above the threshold
    critical_hubs = [
        entry for entry in all_centrality
        if entry["label"] == "Role"
        and entry["betweenness_centrality"] >= hub_threshold
    ]

    return {
        "all_centrality": all_centrality,
        "critical_hubs": critical_hubs,
        "hub_threshold": hub_threshold,
        "total_nodes": G.number_of_nodes(),
        "total_hubs": len(critical_hubs),
    }
