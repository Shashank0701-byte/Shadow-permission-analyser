from app.core.database import get_session


def find_escalation_paths(user):

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