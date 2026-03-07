"""
Build the IAM permission graph in Neo4j from either a simulated dataset
or a real AWS IAM export dataset.

Supports two dataset formats:

1. Simulator dataset (iam_sample.json)
   keys:
   users, roles, resources, assignments, assume, permissions

2. AWS export dataset (aws_iam_data.json)
   keys:
   users, roles, policies, user_roles, role_policies

Design decisions
----------------
* MERGE is used everywhere to keep graph idempotent.
* Resources contain a sensitivity score for risk analysis.
* Policies are treated as intermediate nodes between roles and resources.
"""

import json
import logging

from app.core.database import get_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataset I/O
# ---------------------------------------------------------------------------

def load_dataset(file_path: str) -> dict:
    """Load dataset JSON file."""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Graph operations
# ---------------------------------------------------------------------------

def clear_graph():
    """Delete all nodes and relationships."""
    with get_session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    logger.info("Graph cleared.")


def _ensure_indexes(session):
    """Create indexes for faster graph lookups."""
    for label in ("User", "Role", "Resource", "Policy"):
        session.run(
            f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.name)"
        )

    logger.info("Indexes ensured.")


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

def build_graph(data: dict):
    """
    Build Neo4j graph from dataset.

    Automatically detects dataset type.
    """

    with get_session() as session:

        _ensure_indexes(session)

        # ------------------------------------------------------------------
        # AWS IAM DATASET
        # ------------------------------------------------------------------

        if "user_roles" in data:

            logger.info("Building graph from AWS IAM dataset.")

            # nodes
            for user in data["users"]:
                session.run(
                    "MERGE (:User {name:$name})",
                    name=user,
                )

            for role in data["roles"]:
                session.run(
                    "MERGE (:Role {name:$name})",
                    name=role,
                )

            for policy in data.get("policies", []):
                session.run(
                    "MERGE (:Policy {name:$name})",
                    name=policy,
                )

            for resource in data.get("resources", []):
                session.run(
                    """
                    MERGE (r:Resource {name:$name})
                    SET r.sensitivity=$sensitivity
                    """,
                    name=resource["name"],
                    sensitivity=resource.get("sensitivity", 1),
                )

            # relationships

            for rel in data["user_roles"]:
                session.run(
                    """
                    MATCH (u:User {name:$user})
                    MATCH (r:Role {name:$role})
                    MERGE (u)-[:HAS_ROLE]->(r)
                    """,
                    user=rel["user"],
                    role=rel["role"],
                )

            for rel in data.get("role_policies", []):
                session.run(
                    """
                    MATCH (r:Role {name:$role})
                    MATCH (p:Policy {name:$policy})
                    MERGE (r)-[:HAS_POLICY]->(p)
                    """,
                    role=rel["role"],
                    policy=rel["policy"],
                )

            for user, role in data.get("assignments", []):
                session.run(
                    """
                    MATCH (u:User {name:$u})
                    MATCH (r:Role {name:$r})
                    MERGE (u)-[:ASSIGNED]->(r)
                    """,
                    u=user,
                    r=role,
                )

            for role_from, role_to in data.get("assume", []):
                session.run(
                    """
                    MATCH (a:Role {name:$r1})
                    MATCH (b:Role {name:$r2})
                    MERGE (a)-[:ASSUME]->(b)
                    """,
                    r1=role_from,
                    r2=role_to,
                )

            for perm in data.get("permissions", []):
                session.run(
                    """
                    MATCH (r:Role {name:$role})
                    MATCH (res:Resource {name:$res})
                    MERGE (r)-[:ACCESS]->(res)
                    """,
                    role=perm["role"],
                    res=perm["resource"],
                )

            logger.info("AWS IAM graph built.")

        # ------------------------------------------------------------------
        # SIMULATOR DATASET
        # ------------------------------------------------------------------

        elif "assignments" in data:

            logger.info("Building graph from simulator dataset.")

            # nodes
            for user in data["users"]:
                session.run(
                    "MERGE (:User {name:$name})",
                    name=user,
                )

            for role in data["roles"]:
                session.run(
                    "MERGE (:Role {name:$name})",
                    name=role,
                )

            for resource in data["resources"]:
                session.run(
                    """
                    MERGE (r:Resource {name:$name})
                    SET r.sensitivity=$sensitivity
                    """,
                    name=resource["name"],
                    sensitivity=resource.get("sensitivity", 1),
                )

            # relationships

            for user, role in data["assignments"]:
                session.run(
                    """
                    MATCH (u:User {name:$u})
                    MATCH (r:Role {name:$r})
                    MERGE (u)-[:ASSIGNED]->(r)
                    """,
                    u=user,
                    r=role,
                )

            for role_from, role_to in data["assume"]:
                session.run(
                    """
                    MATCH (a:Role {name:$r1})
                    MATCH (b:Role {name:$r2})
                    MERGE (a)-[:ASSUME]->(b)
                    """,
                    r1=role_from,
                    r2=role_to,
                )

            for role, resource in data["permissions"]:
                session.run(
                    """
                    MATCH (r:Role {name:$role})
                    MATCH (res:Resource {name:$res})
                    MERGE (r)-[:ACCESS]->(res)
                    """,
                    role=role,
                    res=resource,
                )

            logger.info("Simulator graph built.")

        else:
            raise ValueError(
                "Unsupported dataset format. Missing expected keys."
            )

    logger.info("Graph construction complete.")