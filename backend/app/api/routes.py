"""Core API routes for the Shadow Permission Analyzer.

Endpoints
---------
POST /simulate           — generate & load a simulated IAM dataset
GET  /graph              — full graph for visualisation
GET  /escalation/{user}  — privilege-escalation analysis
GET  /blast-radius/{user} — blast-radius analysis
"""

import traceback

from fastapi import APIRouter, HTTPException, Query

from app.simulation.simulator import generate_dataset
from app.graph.graph_builder import clear_graph, build_graph
from app.graph.queries import get_full_graph
from app.analysis.escalation import find_escalation_paths
from app.analysis.blast_radius import compute_blast_radius

router = APIRouter()


# ── POST /simulate ──────────────────────────────────────────────────────────

@router.post("/simulate")
def simulate(
    num_users: int = Query(5, ge=1, le=50, description="Extra random users"),
    num_roles: int = Query(4, ge=1, le=30, description="Extra random roles"),
    num_resources: int = Query(3, ge=1, le=20, description="Extra random resources"),
    seed: int | None = Query(None, description="RNG seed for reproducibility"),
):
    """Generate a simulated IAM dataset, load it into Neo4j, and return it."""
    try:
        dataset = generate_dataset(
            num_extra_users=num_users,
            num_extra_roles=num_roles,
            num_extra_resources=num_resources,
            seed=seed,
        )
        clear_graph()
        build_graph(dataset)
        return {
            "status": "ok",
            "message": "Simulation loaded into Neo4j.",
            "dataset_summary": {
                "users": len(dataset["users"]),
                "roles": len(dataset["roles"]),
                "resources": len(dataset["resources"]),
                "assignments": len(dataset["assignments"]),
                "assume_relations": len(dataset["assume"]),
                "permissions": len(dataset["permissions"]),
            },
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
