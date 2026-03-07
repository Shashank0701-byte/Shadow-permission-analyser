from fastapi import APIRouter
from app.core.database import get_session

router = APIRouter()

@router.get("/graph")
def get_graph():

    query = """
    MATCH (n)-[r]->(m)
    RETURN n,r,m
    """

    nodes = {}
    edges = []

    with get_session() as session:
        result = session.run(query)

        for record in result:
            n = record["n"]
            m = record["m"]
            r = record["r"]

            nodes[n.id] = {
                "id": n.id,
                "label": list(n.labels)[0],
                "name": n.get("name")
            }

            nodes[m.id] = {
                "id": m.id,
                "label": list(m.labels)[0],
                "name": m.get("name")
            }

            edges.append({
                "source": n.id,
                "target": m.id,
                "type": r.type
            })

    return {
        "nodes": list(nodes.values()),
        "links": edges
    }