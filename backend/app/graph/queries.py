from app.core.database import get_session


def get_user_permission_paths(user):
    """Return raw privilege-escalation paths from Neo4j for a given user.

    This is a data-access helper — it runs the Cypher query and returns
    the raw Neo4j path objects.  Any further analysis (filtering,
    scoring, etc.) belongs in the analysis layer.
    """
    query = """
    MATCH path =
    (u:User {name:$user})
    -[:ASSIGNED|ASSUME*]->
    (r:Role)-[:ACCESS]->
    (res:Resource)
    RETURN path
    """

    with get_session() as session:
        result = session.run(query, user=user)
        return [record["path"] for record in result]


def get_full_graph():
    """Return all nodes and edges in the graph for visualization.

    Transforms raw Neo4j records into a serializable dict with
    ``nodes`` and ``links`` lists suitable for a force-directed graph.
    """
    query = "MATCH (n)-[r]->(m) RETURN n, r, m"

    nodes = {}
    edges = []

    with get_session() as session:
        result = session.run(query)

        for record in result:
            n = record["n"]
            m = record["m"]
            r = record["r"]

            for node in (n, m):
                nodes[node.element_id] = {
                    "id": node.element_id,
                    "label": list(node.labels)[0],
                    "name": node.get("name"),
                }

            edges.append({
                "source": n.element_id,
                "target": m.element_id,
                "type": r.type,
            })

    return {"nodes": list(nodes.values()), "links": edges}