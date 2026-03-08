"""Cypher query helpers for the IAM permission graph.

All functions return **serialisable dicts / lists** that can be passed
straight into a FastAPI JSON response.

Query optimisation notes
------------------------
* Graph-builder creates **indexes** on ``User.name``, ``Role.name`` and
  ``Resource.name``, so ``MATCH (u:User {name: $user})`` resolves via
  index look-up rather than a full label scan.
* Variable-length patterns ``[:ASSIGNED|ASSUME*]`` leverage the index on
  the *starting* node and then traverse relationships — this is the most
  efficient approach for privilege-escalation path detection.
"""

from app.core.database import get_session


# ---------------------------------------------------------------------------
# Escalation / path queries
# ---------------------------------------------------------------------------

def get_user_permission_paths(user: str) -> list[dict]:
    """Return all privilege-escalation paths from *user* to any resource.

    Each returned dict contains:
    * ``nodes``  — ordered list of nodes in the path
    * ``edges``  — ordered list of relationship types
    * ``depth``  — number of hops
    * ``resource`` — target resource metadata (name + sensitivity)
    """
    query = """
    MATCH path = (u:User {name: $user})
                 -[:ASSIGNED|ASSUME*]->
                 (r:Role)-[:ACCESS]->
                 (res:Resource)
    RETURN path,
           length(path)       AS depth,
           res.name            AS resource_name,
           res.sensitivity     AS sensitivity
    """

    paths = []
    with get_session() as session:
        for record in session.run(query, user=user):
            p = record["path"]
            nodes = [
                {
                    "id": node.element_id,
                    "label": list(node.labels)[0],
                    "name": node.get("name"),
                    "sensitivity": node.get("sensitivity"),
                }
                for node in p.nodes
            ]
            edges = [rel.type for rel in p.relationships]
            paths.append({
                "nodes": nodes,
                "edges": edges,
                "depth": record["depth"],
                "resource": {
                    "name": record["resource_name"],
                    "sensitivity": record["sensitivity"],
                },
            })
    return paths


def get_shortest_escalation_path(user: str) -> dict | None:
    """Return the shortest privilege-escalation path for *user*, or None."""
    query = """
    MATCH (u:User {name: $user}), (res:Resource)
    MATCH path = shortestPath(
        (u)-[:ASSIGNED|ASSUME|ACCESS*]->(res)
    )
    RETURN path,
           length(path)   AS depth,
           res.name        AS resource_name,
           res.sensitivity AS sensitivity
    ORDER BY depth
    LIMIT 1
    """

    with get_session() as session:
        record = session.run(query, user=user).single()
        if record is None:
            return None

        p = record["path"]
        nodes = [
            {
                "id": node.element_id,
                "label": list(node.labels)[0],
                "name": node.get("name"),
                "sensitivity": node.get("sensitivity"),
            }
            for node in p.nodes
        ]
        edges = [rel.type for rel in p.relationships]
        return {
            "nodes": nodes,
            "edges": edges,
            "depth": record["depth"],
            "resource": {
                "name": record["resource_name"],
                "sensitivity": record["sensitivity"],
            },
        }


# ---------------------------------------------------------------------------
# Blast radius queries
# ---------------------------------------------------------------------------

def get_reachable_resources(user: str) -> list[dict]:
    """Return every resource reachable from *user* with path length.

    Used by the blast-radius analysis to compute impact when a user is
    compromised.
    """
    query = """
    MATCH path = (u:User {name: $user})
                 -[:ASSIGNED|ASSUME*]->
                 (r:Role)-[:ACCESS]->
                 (res:Resource)
    RETURN DISTINCT res.name        AS resource_name,
                    res.sensitivity AS sensitivity,
                    min(length(path)) AS min_path_length
    """

    resources = []
    with get_session() as session:
        for record in session.run(query, user=user):
            resources.append({
                "name": record["resource_name"],
                "sensitivity": record["sensitivity"],
                "min_path_length": record["min_path_length"],
            })
    return resources


def get_sensitive_resources(min_sensitivity: int = 4) -> list[dict]:
    """Return resources whose sensitivity is at or above the threshold."""
    query = """
    MATCH (res:Resource)
    WHERE res.sensitivity >= $min_sensitivity
    RETURN res.name AS name, res.sensitivity AS sensitivity
    ORDER BY res.sensitivity DESC
    """

    with get_session() as session:
        return [
            {"name": r["name"], "sensitivity": r["sensitivity"]}
            for r in session.run(query, min_sensitivity=min_sensitivity)
        ]


# ---------------------------------------------------------------------------
# Full-graph visualisation
# ---------------------------------------------------------------------------

def get_full_graph(highlight_user: str | None = None) -> dict:
    """Return all nodes and edges for the force-directed graph visualisation."""
    query_all = "MATCH (n)-[r]->(m) RETURN n, r, m"
    
    if highlight_user:
        query_escalation = """
        MATCH path = (u:User {name: $highlight_user})-[:ASSIGNED|ASSUME*]->(r:Role)-[:ACCESS]->(res:Resource)
        RETURN path
        ORDER BY length(path) ASC
        LIMIT 1
        """
    else:
        query_escalation = """
        MATCH path = (u:User)-[:ASSIGNED|ASSUME*]->(r:Role)-[:ACCESS]->(res:Resource)
        RETURN path
        ORDER BY length(path) ASC
        LIMIT 1
        """

    nodes = {}
    edges = []
    escalation_edge_ids = set()

    with get_session() as session:
        # Identify all edges that are part of an escalation path
        params = {"highlight_user": highlight_user} if highlight_user else {}
        for record in session.run(query_escalation, **params):
            for rel in record["path"].relationships:
                escalation_edge_ids.add(rel.element_id)

        # Build nodes
        for record in session.run("MATCH (n) RETURN n"):
            node = record["n"]
            nodes[node.element_id] = {
                "id": node.element_id,
                "label": list(node.labels)[0] if node.labels else "Unknown",
                "name": node.get("name"),
                "sensitivity": node.get("sensitivity"),
            }

        # Build edges
        for record in session.run("MATCH (n)-[r]->(m) RETURN n, r, m"):
            n = record["n"]
            m = record["m"]
            r = record["r"]

            edges.append({
                "source": n.element_id,
                "target": m.element_id,
                "type": r.type,
                "is_escalation": r.element_id in escalation_edge_ids
            })

    return {"nodes": list(nodes.values()), "links": edges}