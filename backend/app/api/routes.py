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
from app.simulation.aws_ingestor import fetch_live_aws_iam_data
from app.graph.graph_builder import clear_graph, build_graph, load_dataset
from app.core.database import get_session
import os
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
    """Run a security analysis on the active Neo4j graph without changing the data.
    """
    try:
        # Get all users currently in the graph
        session = get_session()
        users = [r[0] for r in session.run("MATCH (n:User) RETURN n.name")]

        # --- Run escalation analysis on every user ---
        user_analyses = []
        for user in users:
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
                "users": len(users),
            },
            "weakest_user": weakest_user,
            "user_analyses": user_analyses,
            "centrality": centrality_result,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /ingest-aws ────────────────────────────────────────────────────────

@router.post("/ingest-aws")
def ingest_aws():
    """Load real AWS IAM dataset into Neo4j and return summary."""
    try:
        # Fetch Live AWS IAM Data via Boto3!
        try:
            dataset = fetch_live_aws_iam_data()
        except Exception as e:
            # Fallback for hackathon demo if AWS credentials fail
            print(f"Failed to fetch live AWS: {e}. Falling back to pre-exported sample data.")
            dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../dataset/aws_iam_data.json"))
            dataset = load_dataset(dataset_path)

        clear_graph()
        build_graph(dataset)

        # --- Run escalation analysis on every user ---
        user_analyses = []
        for user in dataset.get("users", []):
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
            "message": "AWS IAM dataset loaded and graph rebuilt.",
            "dataset_summary": {
                "users": len(dataset.get("users", [])),
                "roles": len(dataset.get("roles", [])),
                "policies": len(dataset.get("policies", [])),
                "user_roles": len(dataset.get("user_roles", [])),
                "role_policies": len(dataset.get("role_policies", []))
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


# ── GET /attack-simulation/{user} ──────────────────────────────────────────

@router.get("/attack-simulation/{user}")
def attack_simulation(user: str):
    """Return step-by-step attack simulation for *user*."""
    try:
        from app.analysis.attack_simulation import generate_attack_steps
        return generate_attack_steps(user)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /remediation/{user} ────────────────────────────────────────────────

@router.get("/remediation/{user}")
def remediation(user: str):
    """Return automatic remediation suggestions for *user*."""
    try:
        from app.analysis.remediation import generate_remediation
        return generate_remediation(user)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
