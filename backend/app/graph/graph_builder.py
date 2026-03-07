"""Build the IAM permission graph in Neo4j from a dataset dict.

Key design decisions
--------------------
* **MERGE** (not CREATE) is used everywhere so the builder is idempotent —
  running it twice on the same dataset never creates duplicate nodes or edges.
* Resources store a ``sensitivity`` property (integer 1-5) used later for
  blast-radius risk scoring.
* The ``clear_graph()`` helper wipes the database before a fresh import.
* ``build_graph`` also creates **indexes** on ``User.name``, ``Role.name``
  and ``Resource.name`` for fast Cypher look-ups.
"""

import json
import logging

from app.core.database import get_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataset I/O
# ---------------------------------------------------------------------------

def load_dataset(file_path: str) -> dict:
    """Load an IAM dataset JSON file (e.g. ``iam_sample.json``)."""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Graph operations
# ---------------------------------------------------------------------------

def clear_graph():
    """Delete every node and relationship in the database."""
    with get_session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    logger.info("Graph cleared.")


def _ensure_indexes(session):
    """Create uniqueness-constraint indexes if they do not exist yet."""
    for label in ("User", "Role", "Resource"):
        session.run(
            f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.name)"
        )
    logger.info("Indexes ensured for User, Role, Resource.")


def build_graph(data: dict):
    """Populate Neo4j with the IAM dataset.

    Parameters
    ----------
    data : dict
        Must contain the keys ``users``, ``roles``, ``resources``,
        ``assignments``, ``assume``, and ``permissions``.
        Compatible with ``iam_sample.json`` and datasets produced by
        ``simulation.simulator.generate_dataset()``.
    """

    with get_session() as session:

        # indexes for fast look-ups
        _ensure_indexes(session)

        # --- nodes -----------------------------------------------------------

        for user in data["users"]:
            session.run(
                "MERGE (:User {name: $name})",
                name=user,
            )

        for role in data["roles"]:
            session.run(
                "MERGE (:Role {name: $name})",
                name=role,
            )

        for resource in data["resources"]:
            session.run(
                "MERGE (r:Resource {name: $name}) "
                "SET r.sensitivity = $sensitivity",
                name=resource["name"],
                sensitivity=resource.get("sensitivity", 1),
            )

        # --- relationships ---------------------------------------------------

        for user, role in data["assignments"]:
            session.run(
                """
                MATCH (u:User {name: $u}), (r:Role {name: $r})
                MERGE (u)-[:ASSIGNED]->(r)
                """,
                u=user,
                r=role,
            )

        for role_from, role_to in data["assume"]:
            session.run(
                """
                MATCH (a:Role {name: $r1}), (b:Role {name: $r2})
                MERGE (a)-[:ASSUME]->(b)
                """,
                r1=role_from,
                r2=role_to,
            )

        for role, resource in data["permissions"]:
            session.run(
                """
                MATCH (r:Role {name: $role}), (res:Resource {name: $res})
                MERGE (r)-[:ACCESS]->(res)
                """,
                role=role,
                res=resource,
            )

    logger.info(
        "Graph built — %d users, %d roles, %d resources.",
        len(data["users"]),
        len(data["roles"]),
        len(data["resources"]),
    )