"""Blast-radius analysis.

If a user account is compromised, this module computes every resource
that becomes reachable through the IAM permission graph.

For each affected resource it returns:
* resource name and sensitivity
* shortest path length from the compromised user
* an individual risk score

The overall response includes a summary with total reachable resources
and an aggregate risk score.
"""

from app.graph.queries import get_reachable_resources


def compute_blast_radius(user: str) -> dict:
    """Return the blast-radius report for a compromised *user*.

    Response schema::

        {
            "user": "Intern_A",
            "total_affected_resources": 3,
            "affected_resources": [
                {
                    "name": "ProductionDB",
                    "sensitivity": 5,
                    "min_path_length": 4,
                    "risk_score": 8.75
                },
                …
            ],
            "aggregate_risk_score": 8.75,
            "risk_level": "CRITICAL"
        }
    """
    resources = get_reachable_resources(user)

    affected = []
    for res in resources:
        score = _compute_risk_score(
            sensitivity=res["sensitivity"],
            path_length=res["min_path_length"],
        )
        affected.append({
            "name": res["name"],
            "sensitivity": res["sensitivity"],
            "min_path_length": res["min_path_length"],
            "risk_score": score,
        })

    # Sort by risk score descending (most dangerous first)
    affected.sort(key=lambda r: r["risk_score"], reverse=True)

    aggregate_score = (
        max(r["risk_score"] for r in affected) if affected else 0.0
    )

    return {
        "user": user,
        "total_affected_resources": len(affected),
        "affected_resources": affected,
        "aggregate_risk_score": round(aggregate_score, 2),
        "risk_level": _classify_risk(aggregate_score),
    }


def _compute_risk_score(sensitivity: int | None, path_length: int) -> float:
    """Compute a 0-10 risk score for a single resource.

    Formula::

        score = (sensitivity / 5) * 10 * proximity_factor

    * ``sensitivity`` ranges 1–5 (default 1 if missing).
    * ``proximity_factor`` = 1 / ln(path_length + 1) — shorter paths
      are riskier because fewer privilege hops are needed.
    """
    import math

    sens = sensitivity if sensitivity is not None else 1
    proximity = 1 / math.log(path_length + 1) if path_length > 0 else 1.0
    raw = (sens / 5) * 10 * proximity
    return round(min(raw, 10.0), 2)


def _classify_risk(score: float) -> str:
    """Map an aggregate risk score to a human-readable level."""
    if score >= 8:
        return "CRITICAL"
    if score >= 6:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"
