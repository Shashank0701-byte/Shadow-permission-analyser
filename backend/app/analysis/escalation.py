"""Privilege-escalation analysis.

Detects paths like ``User → Role → Role → Resource`` by traversing
the IAM permission graph.  Each returned path includes:

* ordered node chain
* relationship types at each hop
* total depth (number of hops)
* target resource metadata (name + sensitivity)

The analysis layer adds domain logic *on top of* the raw Cypher
queries in ``app.graph.queries``.
"""

from app.graph.queries import get_user_permission_paths, get_shortest_escalation_path


def find_escalation_paths(user: str) -> dict:
    """Return full escalation analysis for *user*.

    Response schema::

        {
            "user": "Intern_A",
            "total_paths": 2,
            "escalation_paths": [ … ],
            "max_depth": 4,
            "sensitive_targets": [ … ],
            "risk_level": "CRITICAL"
        }
    """
    paths = get_user_permission_paths(user)
    shortest = get_shortest_escalation_path(user)

    # Identify unique sensitive targets
    sensitive_targets = []
    seen = set()
    for p in paths:
        res = p["resource"]
        if res["name"] not in seen and res["sensitivity"] is not None and res["sensitivity"] >= 4:
            sensitive_targets.append(res)
            seen.add(res["name"])

    max_depth = max((p["depth"] for p in paths), default=0)

    # Risk classification
    risk_level = _classify_risk(paths, sensitive_targets)

    return {
        "user": user,
        "total_paths": len(paths),
        "escalation_paths": paths,
        "shortest_path": shortest,
        "max_depth": max_depth,
        "sensitive_targets": sensitive_targets,
        "risk_level": risk_level,
    }


def _classify_risk(paths: list[dict], sensitive_targets: list[dict]) -> str:
    """Classify risk based on path count and target sensitivity.

    * ``CRITICAL`` — reaches a sensitive resource (sensitivity ≥ 4)
    * ``HIGH``     — multiple escalation paths exist
    * ``MEDIUM``   — a single escalation path exists
    * ``LOW``      — no escalation paths
    """
    if sensitive_targets:
        return "CRITICAL"
    if len(paths) > 1:
        return "HIGH"
    if len(paths) == 1:
        return "MEDIUM"
    return "LOW"
