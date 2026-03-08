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
        with get_session() as session:
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
        dataset = fetch_live_aws_iam_data()

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
def get_graph(highlight_user: str | None = Query(None, description="User to highlight escalation paths for")):
    """Return the full permission graph for visualisation."""
    try:
        return get_full_graph(highlight_user)
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


# ── POST /reassign-role ────────────────────────────────────────────────────

@router.post("/reassign-role")
def reassign_role(
    user: str = Query(..., description="User to reassign"),
    old_role: str = Query(None, description="Current role to remove (optional)"),
    new_role: str = Query(..., description="New role to assign"),
):
    """Reassign a user to a different role in LIVE AWS IAM + Neo4j.

    Steps:
    1. Capture the user's current risk score (before)
    2. Modify real AWS trust policies via boto3
    3. Re-ingest fresh AWS data
    4. Rebuild Neo4j graph from verified AWS state
    5. Re-run analysis (after)
    6. Return before/after comparison
    """
    import boto3
    import json

    try:
        iam = boto3.client("iam")
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]

        # --- Before: capture current risk ---
        before_analysis = find_escalation_paths(user)

        # --- Determine if user is a User or Role (for ARN construction) ---
        # Check if 'user' exists as an IAM user
        is_iam_user = False
        try:
            iam.get_user(UserName=user)
            is_iam_user = True
        except iam.exceptions.NoSuchEntityException:
            is_iam_user = False

        if is_iam_user:
            user_arn = f"arn:aws:iam::{account_id}:user/{user}"
        else:
            user_arn = f"arn:aws:iam::{account_id}:role/{user}"

        # --- Step 1: Remove user from old role's trust policy ---
        if old_role:
            try:
                old_role_data = iam.get_role(RoleName=old_role)["Role"]
                old_trust = old_role_data["AssumeRolePolicyDocument"]

                # First check if the user is actually in this role's trust policy
                user_found_in_old_role = False
                for stmt in old_trust.get("Statement", []):
                    principal_aws = stmt.get("Principal", {}).get("AWS", "")
                    if isinstance(principal_aws, str) and principal_aws == user_arn:
                        user_found_in_old_role = True
                    elif isinstance(principal_aws, list) and user_arn in principal_aws:
                        user_found_in_old_role = True

                if user_found_in_old_role:
                    # Filter out statements that grant this user access
                    new_statements = []
                    for stmt in old_trust.get("Statement", []):
                        principal_aws = stmt.get("Principal", {}).get("AWS", "")
                        if isinstance(principal_aws, str):
                            if principal_aws != user_arn:
                                new_statements.append(stmt)
                        elif isinstance(principal_aws, list):
                            filtered = [p for p in principal_aws if p != user_arn]
                            if filtered:
                                stmt["Principal"]["AWS"] = filtered if len(filtered) > 1 else filtered[0]
                                new_statements.append(stmt)

                    if new_statements:
                        old_trust["Statement"] = new_statements
                        iam.update_assume_role_policy(
                            RoleName=old_role,
                            PolicyDocument=json.dumps(old_trust),
                        )
                    else:
                        placeholder = {
                            "Version": "2012-10-17",
                            "Statement": [{
                                "Effect": "Deny",
                                "Principal": {"AWS": "*"},
                                "Action": "sts:AssumeRole",
                            }],
                        }
                        iam.update_assume_role_policy(
                            RoleName=old_role,
                            PolicyDocument=json.dumps(placeholder),
                        )
                # else: user not in old role — skip removal silently
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to update trust policy on {old_role}: {str(e)}",
                )

        # --- Step 2: Add user to new role's trust policy ---
        try:
            new_role_data = iam.get_role(RoleName=new_role)["Role"]
            new_trust = new_role_data["AssumeRolePolicyDocument"]

            # Check if user is already in the trust policy
            already_present = False
            for stmt in new_trust.get("Statement", []):
                principal_aws = stmt.get("Principal", {}).get("AWS", "")
                if isinstance(principal_aws, str) and principal_aws == user_arn:
                    already_present = True
                elif isinstance(principal_aws, list) and user_arn in principal_aws:
                    already_present = True

            if not already_present:
                # Remove any Deny placeholder statements left from previous removals
                new_trust["Statement"] = [
                    s for s in new_trust["Statement"]
                    if s.get("Effect") != "Deny"
                ]
                # Add a new statement granting this user access
                new_trust["Statement"].append({
                    "Effect": "Allow",
                    "Principal": {"AWS": user_arn},
                    "Action": "sts:AssumeRole",
                })
                iam.update_assume_role_policy(
                    RoleName=new_role,
                    PolicyDocument=json.dumps(new_trust),
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to update trust policy on {new_role}: {str(e)}",
            )

        # --- Step 3: Re-ingest fresh AWS data & rebuild graph ---
        dataset = fetch_live_aws_iam_data()
        clear_graph()
        build_graph(dataset)

        # --- Step 4: Re-run analysis on verified data ---
        after_analysis = find_escalation_paths(user)
        centrality_result = find_critical_hubs(hub_threshold=0.1)

        # --- Build comparison ---
        risk_delta = after_analysis["overall_risk_score"] - before_analysis["overall_risk_score"]

        return {
            "status": "ok",
            "message": f"AWS IAM updated — {user}: {old_role or '(none)'} → {new_role}",
            "aws_changes": {
                "removed_from": old_role,
                "added_to": new_role,
                "account_id": account_id,
            },
            "before": {
                "risk_score": before_analysis["overall_risk_score"],
                "risk_level": before_analysis["risk_level"],
                "total_paths": before_analysis["total_paths"],
            },
            "after": {
                "risk_score": after_analysis["overall_risk_score"],
                "risk_level": after_analysis["risk_level"],
                "total_paths": after_analysis["total_paths"],
            },
            "risk_delta": round(risk_delta, 2),
            "risk_increased": risk_delta > 0,
            "user_analysis": after_analysis,
            "centrality": centrality_result,
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /reassign-roles-batch ─────────────────────────────────────────────

from pydantic import BaseModel
from typing import List, Optional

class RoleChange(BaseModel):
    user: str
    old_role: Optional[str] = None
    new_role: str

class BatchReassignRequest(BaseModel):
    changes: List[RoleChange]

@router.post("/reassign-roles-batch")
def reassign_roles_batch(req: BatchReassignRequest):
    """Apply multiple role reassignments to live AWS IAM in one batch.

    1. Capture before state (risk scores for all affected users)
    2. Apply all trust policy changes to AWS
    3. Single re-ingestion from AWS
    4. Single graph rebuild
    5. Re-run analysis
    6. Return before/after comparison
    """
    import boto3
    import json

    if not req.changes:
        raise HTTPException(status_code=400, detail="No changes provided")

    try:
        iam = boto3.client("iam")
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]

        applied = []
        errors = []

        # --- Before: capture risk for all affected users ---
        affected_users = list({c.user for c in req.changes})
        before_scores = {}
        for u in affected_users:
            try:
                analysis = find_escalation_paths(u)
                before_scores[u] = {
                    "risk_score": analysis["overall_risk_score"],
                    "risk_level": analysis["risk_level"],
                    "total_paths": analysis["total_paths"],
                }
            except Exception:
                before_scores[u] = {"risk_score": 0, "risk_level": "LOW", "total_paths": 0}

        # --- Apply each change to AWS ---
        for change in req.changes:
            try:
                # Determine ARN
                is_iam_user = False
                try:
                    iam.get_user(UserName=change.user)
                    is_iam_user = True
                except iam.exceptions.NoSuchEntityException:
                    pass

                user_arn = f"arn:aws:iam::{account_id}:{'user' if is_iam_user else 'role'}/{change.user}"

                # Remove from old role
                if change.old_role:
                    try:
                        old_role_data = iam.get_role(RoleName=change.old_role)["Role"]
                        old_trust = old_role_data["AssumeRolePolicyDocument"]

                        user_found = any(
                            (isinstance(s.get("Principal", {}).get("AWS", ""), str) and s["Principal"]["AWS"] == user_arn)
                            or (isinstance(s.get("Principal", {}).get("AWS", []), list) and user_arn in s["Principal"]["AWS"])
                            for s in old_trust.get("Statement", [])
                        )

                        if user_found:
                            new_stmts = []
                            for stmt in old_trust.get("Statement", []):
                                p = stmt.get("Principal", {}).get("AWS", "")
                                if isinstance(p, str):
                                    if p != user_arn:
                                        new_stmts.append(stmt)
                                elif isinstance(p, list):
                                    filtered = [x for x in p if x != user_arn]
                                    if filtered:
                                        stmt["Principal"]["AWS"] = filtered if len(filtered) > 1 else filtered[0]
                                        new_stmts.append(stmt)

                            if new_stmts:
                                old_trust["Statement"] = new_stmts
                                iam.update_assume_role_policy(RoleName=change.old_role, PolicyDocument=json.dumps(old_trust))
                            else:
                                iam.update_assume_role_policy(RoleName=change.old_role, PolicyDocument=json.dumps({
                                    "Version": "2012-10-17",
                                    "Statement": [{"Effect": "Deny", "Principal": {"AWS": "*"}, "Action": "sts:AssumeRole"}],
                                }))
                    except Exception as e:
                        errors.append(f"Remove {change.user} from {change.old_role}: {str(e)}")

                # Add to new role
                try:
                    new_role_data = iam.get_role(RoleName=change.new_role)["Role"]
                    new_trust = new_role_data["AssumeRolePolicyDocument"]

                    already = any(
                        (isinstance(s.get("Principal", {}).get("AWS", ""), str) and s["Principal"]["AWS"] == user_arn)
                        or (isinstance(s.get("Principal", {}).get("AWS", []), list) and user_arn in s["Principal"]["AWS"])
                        for s in new_trust.get("Statement", [])
                    )

                    if not already:
                        new_trust["Statement"] = [s for s in new_trust["Statement"] if s.get("Effect") != "Deny"]
                        new_trust["Statement"].append({
                            "Effect": "Allow",
                            "Principal": {"AWS": user_arn},
                            "Action": "sts:AssumeRole",
                        })
                        iam.update_assume_role_policy(RoleName=change.new_role, PolicyDocument=json.dumps(new_trust))
                except Exception as e:
                    errors.append(f"Add {change.user} to {change.new_role}: {str(e)}")
                    continue

                applied.append(f"{change.user}: {change.old_role or '(none)'} → {change.new_role}")

            except Exception as e:
                errors.append(f"{change.user}: {str(e)}")

        # --- Single re-ingestion & rebuild ---
        dataset = fetch_live_aws_iam_data()
        clear_graph()
        build_graph(dataset)

        # --- After: re-run analysis ---
        after_scores = {}
        for u in affected_users:
            try:
                analysis = find_escalation_paths(u)
                after_scores[u] = {
                    "risk_score": analysis["overall_risk_score"],
                    "risk_level": analysis["risk_level"],
                    "total_paths": analysis["total_paths"],
                }
            except Exception:
                after_scores[u] = {"risk_score": 0, "risk_level": "LOW", "total_paths": 0}

        centrality_result = find_critical_hubs(hub_threshold=0.1)

        return {
            "status": "ok",
            "applied": applied,
            "errors": errors,
            "before": before_scores,
            "after": after_scores,
            "centrality": centrality_result,
            "account_id": account_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /temporary-access ─────────────────────────────────────────────────

import os
import json
import threading
from datetime import datetime, timedelta
import boto3
import traceback

SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "temp_sessions.json")
_sessions_lock = threading.Lock()

def _load_sessions():
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding sessions: {e}")
    return {}

def _save_sessions(sessions):
    temp_file = SESSIONS_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(sessions, f, indent=2)
    os.replace(temp_file, SESSIONS_FILE)

class TempAccessRequest(BaseModel):
    user: str
    old_role: Optional[str] = None
    new_role: str
    duration_seconds: int

def sync_rollback_temp_access(req_data: dict):
    """Revert the trust policy mapping back to its original state synchronously."""
    try:
        iam = boto3.client("iam")
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]

        is_iam_user = False
        try:
            iam.get_user(UserName=req_data["user"])
            is_iam_user = True
        except iam.exceptions.NoSuchEntityException:
            pass

        user_arn = f"arn:aws:iam::{account_id}:{'user' if is_iam_user else 'role'}/{req_data['user']}"

        # 1. Remove from new_role (the temporary assignment)
        try:
            new_role_data = iam.get_role(RoleName=req_data["new_role"])["Role"]
            new_trust = new_role_data["AssumeRolePolicyDocument"]
            new_stmts = []
            for stmt in new_trust.get("Statement", []):
                p = stmt.get("Principal", {}).get("AWS", "")
                if isinstance(p, str):
                    if p != user_arn: new_stmts.append(stmt)
                elif isinstance(p, list):
                    filtered = [x for x in p if x != user_arn]
                    if filtered:
                        stmt["Principal"]["AWS"] = filtered if len(filtered) > 1 else filtered[0]
                        new_stmts.append(stmt)
            if new_stmts:
                new_trust["Statement"] = new_stmts
                iam.update_assume_role_policy(RoleName=req_data["new_role"], PolicyDocument=json.dumps(new_trust))
            else:
                iam.update_assume_role_policy(RoleName=req_data["new_role"], PolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{"Effect": "Deny", "Principal": {"AWS": "*"}, "Action": "sts:AssumeRole"}]
                }))
        except Exception as e:
            print(f"Rollback error (Remove from {req_data['new_role']}):", e)

        # 2. Add back to old_role (if there was one)
        if req_data.get("old_role"):
            try:
                old_role_data = iam.get_role(RoleName=req_data["old_role"])["Role"]
                old_trust = old_role_data["AssumeRolePolicyDocument"]
                already = False
                for stmt in old_trust.get("Statement", []):
                    p = stmt.get("Principal", {}).get("AWS", "")
                    if (isinstance(p, str) and p == user_arn) or (isinstance(p, list) and user_arn in p):
                        already = True
                if not already:
                    old_trust["Statement"] = [s for s in old_trust.get("Statement", []) if s.get("Effect") != "Deny"]
                    old_trust["Statement"].append({
                        "Effect": "Allow",
                        "Principal": {"AWS": user_arn},
                        "Action": "sts:AssumeRole"
                    })
                    iam.update_assume_role_policy(RoleName=req_data["old_role"], PolicyDocument=json.dumps(old_trust))
            except Exception as e:
                print(f"Rollback error (Add to {req_data['old_role']}):", e)

        # 3. Trigger graph rebuild
        dataset = fetch_live_aws_iam_data()
        clear_graph()
        build_graph(dataset)
        print(f"Rollback completed for {req_data['user']}: {req_data['new_role']} -> {req_data.get('old_role') or 'None'}")
        return True
    except Exception as e:
        print("Rollback critical error:", e)
        return False


def _reconciler_loop():
    import time
    from datetime import datetime
    while True:
        try:
            with _sessions_lock:
                sessions = _load_sessions()
            now = datetime.now()
            expired = []
            
            for user, info in sessions.items():
                if now > datetime.fromisoformat(info["expires_at"]):
                    expired.append((user, info))
                    
            for user, info in expired:
                info["user"] = user
                success = sync_rollback_temp_access(info)
                if success:
                    with _sessions_lock:
                        sessions = _load_sessions()
                        if user in sessions:
                            del sessions[user]
                        _save_sessions(sessions)
                else:
                    print(f"Rollback failed for {user}, leaving session for retry.")
                
            time.sleep(5)
        except Exception as e:
            print(f"Reconciler error: {e}")
            time.sleep(5)

@router.on_event("startup")
def startup_event():
    threading.Thread(target=_reconciler_loop, daemon=True).start()


@router.post("/temporary-access")
def grant_temporary_access(req: TempAccessRequest):
    """
    Grants temporary elevated privileged access.
    Instantly changes live AWS, and registers a durable session for the background reconciler to revert.
    """
    try:
        with _sessions_lock:
            sessions = _load_sessions()
            
            # Check if already active
            if req.user in sessions:
                raise HTTPException(status_code=400, detail=f"{req.user} already has an active temporary session")

        # Reuse batch logic
        res = reassign_roles_batch(BatchReassignRequest(changes=[RoleChange(user=req.user, old_role=req.old_role, new_role=req.new_role)]))

        # Register durable session
        expires_time = datetime.now() + timedelta(seconds=req.duration_seconds)
        with _sessions_lock:
            sessions = _load_sessions()
            sessions[req.user] = {
                "expires_at": expires_time.isoformat(),
                "duration": req.duration_seconds,
                "old_role": req.old_role,
                "new_role": req.new_role
            }
            _save_sessions(sessions)

        # Extend response
        res["expires_at"] = sessions[req.user]["expires_at"]
        return res
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/temporary-sessions")
def get_temporary_sessions():
    """Return list of active temporary time-bound sessions and when they expire"""
    with _sessions_lock:
        sessions = _load_sessions()

    result = []
    for user, info in sessions.items():
        result.append({
            "user": user,
            "old_role": info["old_role"],
            "new_role": info["new_role"],
            "expires_at": info["expires_at"],
            "duration": info["duration"]
        })
    return {"sessions": result}

