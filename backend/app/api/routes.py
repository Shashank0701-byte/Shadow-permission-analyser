"""Core API routes for the Shadow Permission Analyzer.

Endpoints
---------
POST /simulate           — generate & load a simulated IAM dataset
GET  /graph              — full graph for visualisation
GET  /escalation/{user}  — privilege-escalation analysis
GET  /blast-radius/{user} — blast-radius analysis
GET  /centrality          — betweenness centrality & critical privilege hubs
"""

import traceback

from fastapi import APIRouter, HTTPException, Query

from app.simulation.simulator import generate_dataset
from app.graph.graph_builder import clear_graph, build_graph
from app.graph.queries import get_full_graph
from app.analysis.escalation import find_escalation_paths
from app.analysis.blast_radius import compute_blast_radius
from app.analysis.centrality import find_critical_hubs

router = APIRouter()


# ── POST /simulate ──────────────────────────────────────────────────────────

@router.post("/simulate")
def simulate(
    num_users: int = Query(5, ge=1, le=50, description="Extra random users"),
    num_roles: int = Query(4, ge=1, le=30, description="Extra random roles"),
    num_resources: int = Query(3, ge=1, le=20, description="Extra random resources"),
    seed: int | None = Query(None, description="RNG seed for reproducibility"),
):
    """Generate a simulated IAM dataset, rebuild the graph, and run analysis.

    Steps:
    1. Clear existing graph
    2. Generate new IAM dataset
    3. Rebuild graph in Neo4j
    4. Run escalation analysis on every user
    5. Identify the weakest user (highest risk score)
    """
    try:
        dataset = generate_dataset(
            num_extra_users=num_users,
            num_extra_roles=num_roles,
            num_extra_resources=num_resources,
            seed=seed,
        )
        clear_graph()
        build_graph(dataset)

        # --- Run escalation analysis on every user ---
        user_analyses = []
        for user in dataset["users"]:
            result = find_escalation_paths(user)
            user_analyses.append(result)

        # --- Find the weakest user (highest overall risk score) ---
        weakest_user = None
        if user_analyses:
            weakest = max(user_analyses, key=lambda a: a.get("overall_risk_score", 0))
            if weakest.get("overall_risk_score", 0) > 0:
                weakest_user = {
                    "user": weakest["user"],
                    "risk_level": weakest["risk_level"],
                    "overall_risk_score": weakest["overall_risk_score"],
                    "total_escalation_paths": weakest["total_paths"],
                    "max_depth": weakest["max_depth"],
                    "sensitive_targets": weakest["sensitive_targets"],
                }

        # --- Run centrality analysis ---
        centrality_result = find_critical_hubs(hub_threshold=0.1)

        return {
            "status": "ok",
            "message": "Simulation loaded, graph rebuilt, and analysis complete.",
            "dataset_summary": {
                "users": len(dataset["users"]),
                "roles": len(dataset["roles"]),
                "resources": len(dataset["resources"]),
                "assignments": len(dataset["assignments"]),
                "assume_relations": len(dataset["assume"]),
                "permissions": len(dataset["permissions"]),
            },
            "weakest_user": weakest_user,
            "user_analyses": user_analyses,
            "centrality": centrality_result,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /graph ──────────────────────────────────────────────────────────────

@router.get("/graph")
def get_graph():
    """Return the full permission graph for visualisation."""
    try:
        return get_full_graph()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /escalation/{user} ──────────────────────────────────────────────────

@router.get("/escalation/{user}")
def escalation(user: str):
    """Return privilege-escalation analysis for *user*."""
    try:
        result = find_escalation_paths(user)
        if result["total_paths"] == 0:
            return {
                **result,
                "message": f"No escalation paths found for user '{user}'.",
            }
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /blast-radius/{user} ────────────────────────────────────────────────

@router.get("/blast-radius/{user}")
def blast_radius(user: str):
    """Return blast-radius analysis for a compromised *user*."""
    try:
        result = compute_blast_radius(user)
        if result["total_affected_resources"] == 0:
            return {
                **result,
                "message": f"No reachable resources found for user '{user}'.",
            }
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /centrality ─────────────────────────────────────────────────────────

@router.get("/centrality")
def centrality(
    hub_threshold: float = Query(
        0.1, ge=0.0, le=1.0,
        description="Min betweenness centrality to flag a Role as a critical hub",
    ),
):
    """Return betweenness centrality scores and critical privilege hubs."""
    try:
        return find_critical_hubs(hub_threshold=hub_threshold)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
