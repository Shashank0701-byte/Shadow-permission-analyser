"""Privilege-escalation analysis.

Detects paths like ``User → Role → Role → Resource`` by traversing
the IAM permission graph.  Each returned path includes:

* ordered node chain
* relationship types at each hop
* total depth (number of hops)
* target resource metadata (name + sensitivity)
* risk score (0–100) based on path length × resource sensitivity

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

    # Attach a risk score to every escalation path
    for p in paths:
        p["risk_score"] = compute_risk_score(
            path_length=p["depth"],
            sensitivity=p["resource"].get("sensitivity"),
        )

    # Overall risk score — highest across all paths
    overall_risk_score = (
        max(p["risk_score"] for p in paths) if paths else 0.0
    )

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
        "overall_risk_score": overall_risk_score,
    }


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

def compute_risk_score(
    path_length: int,
    sensitivity: int | None,
    *,
    max_path_length: int = 10,
    max_sensitivity: int = 5,
) -> float:
    """Compute a normalized risk score in the range **0 – 100**.

    Formula::

        raw  = path_length × resource_sensitivity
        score = (raw / theoretical_max) × 100

    where ``theoretical_max = max_path_length × max_sensitivity``.

    Parameters
    ----------
    path_length : int
        Number of hops from the user to the resource.
    sensitivity : int | None
        Resource sensitivity (1–5).  Defaults to **1** when ``None``.
    max_path_length : int
        Upper-bound path length used for normalisation (default 10).
    max_sensitivity : int
        Upper-bound sensitivity used for normalisation (default 5).

    Returns
    -------
    float
        Risk score clamped to [0, 100], rounded to two decimals.
    """
    sens = sensitivity if sensitivity is not None else 1
    raw = path_length * sens
    theoretical_max = max_path_length * max_sensitivity  # 50 by default
    normalised = (raw / theoretical_max) * 100 if theoretical_max > 0 else 0.0
    return round(min(max(normalised, 0.0), 100.0), 2)


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
