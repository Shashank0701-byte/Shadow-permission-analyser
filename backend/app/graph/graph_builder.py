import json
from app.core.database import get_session


def load_dataset(file_path):
    with open(file_path) as f:
        return json.load(f)


def build_graph(data):

    with get_session() as session:

        # create users
        for user in data["users"]:
            session.run(
                "MERGE (:User {name:$name})",
                name=user
            )

        # create roles
        for role in data["roles"]:
            session.run(
                "MERGE (:Role {name:$name})",
                name=role
            )

        # create resources
        for r in data["resources"]:
            session.run(
                "MERGE (:Resource {name:$name, sensitivity:$s})",
                name=r["name"],
                s=r["sensitivity"]
            )

        # assignments
        for user, role in data["assignments"]:
            session.run(
                """
                MATCH (u:User {name:$u}),
                      (r:Role {name:$r})
                MERGE (u)-[:ASSIGNED]->(r)
                """,
                u=user,
                r=role
            )

        # assume role
        for r1, r2 in data["assume"]:
            session.run(
                """
                MATCH (a:Role {name:$r1}),
                      (b:Role {name:$r2})
                MERGE (a)-[:ASSUME]->(b)
                """,
                r1=r1,
                r2=r2
            )

        # permissions
        for role, res in data["permissions"]:
            session.run(
                """
                MATCH (r:Role {name:$role}),
                      (res:Resource {name:$res})
                MERGE (r)-[:ACCESS]->(res)
                """,
                role=role,
                res=res
            )