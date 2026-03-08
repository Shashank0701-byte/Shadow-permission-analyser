"""Automatic remediation suggestions.

When a privilege escalation path is detected, this module analyzes the
path to determine the "weakest edge" — the single relationship whose
removal would break the chain with minimal disruption — and generates
specific, actionable AWS CLI remediation commands.

Public API
----------
``generate_remediation(user)``
    Returns prioritized remediation suggestions for all escalation paths.
"""

from app.graph.queries import get_user_permission_paths, get_shortest_escalation_path
from app.analysis.centrality import _build_networkx_graph
import networkx as nx


def generate_remediation(user: str) -> dict:
    """Generate remediation suggestions for escalation paths of *user*.

    Returns
    -------
    dict
        ``user``
            The identity being analyzed.
        ``total_issues``
            Number of escalation paths found.
        ``recommendations``
            Prioritized list of fixes.
        ``weakest_edge``
            The single most impactful edge to remove.
    """
    paths = get_user_permission_paths(user)
    shortest = get_shortest_escalation_path(user)

    if not paths:
        return {
            "user": user,
            "total_issues": 0,
            "recommendations": [],
            "weakest_edge": None,
            "message": f"No escalation paths found for user '{user}'. No remediation needed.",
        }

    recommendations = []

    # ── 1. Find the weakest edge (most impactful to remove) ──────────
    weakest_edge = _find_weakest_edge(shortest) if shortest else None

    if weakest_edge:
        recommendations.append({
            "priority": "CRITICAL",
            "title": f"Remove {weakest_edge['type']} relationship: {weakest_edge['source']} → {weakest_edge['target']}",
            "description": (
                f"This is the single most impactful fix. Removing the "
                f"'{weakest_edge['type']}' relationship between "
                f"'{weakest_edge['source']}' and '{weakest_edge['target']}' "
                f"would break the entire escalation chain."
            ),
            "aws_cli": _generate_fix_command(weakest_edge),
            "impact": "Breaks the primary escalation path completely",
        })

    # ── 2. Analyze each path for specific issues ─────────────────────
    seen_fixes = set()

    for path in paths:
        nodes_list = path.get("nodes", [])
        chain = [n["name"] for n in nodes_list] if isinstance(nodes_list, list) and nodes_list and isinstance(nodes_list[0], dict) else nodes_list
        rels = path.get("edges", path.get("relationships", []))
        resource = path.get("resource", {})

        for i, rel_type in enumerate(rels):
            source = chain[i] if i < len(chain) else "?"
            target = chain[i + 1] if i + 1 < len(chain) else "?"
            fix_key = f"{rel_type}:{source}:{target}"

            if fix_key in seen_fixes:
                continue
            seen_fixes.add(fix_key)

            if rel_type == "ASSUME":
                recommendations.append({
                    "priority": "HIGH",
                    "title": f"Restrict AssumeRole: {source} → {target}",
                    "description": (
                        f"Role '{source}' can assume role '{target}'. "
                        f"Update the trust policy of '{target}' to deny "
                        f"assumption from '{source}', or restrict the "
                        f"sts:AssumeRole permission on '{source}'."
                    ),
                    "aws_cli": (
                        f"# Option A: Remove AssumeRole from source role's policy\n"
                        f"aws iam put-role-policy --role-name {source} \\\n"
                        f"  --policy-name DenyAssumeEscalation \\\n"
                        f"  --policy-document '{{\n"
                        f'    "Version": "2012-10-17",\n'
                        f'    "Statement": [{{\n'
                        f'      "Effect": "Deny",\n'
                        f'      "Action": "sts:AssumeRole",\n'
                        f'      "Resource": "arn:aws:iam::*:role/{target}"\n'
                        f"    }}]\n"
                        f"  }}'\n\n"
                        f"# Option B: Update trust policy of target role\n"
                        f"aws iam update-assume-role-policy --role-name {target} \\\n"
                        f"  --policy-document '<restrictive-trust-policy.json>'"
                    ),
                    "impact": f"Prevents {source} from escalating to {target}",
                })

            elif rel_type == "ACCESS" and resource.get("sensitivity", 0) >= 4:
                recommendations.append({
                    "priority": "HIGH",
                    "title": f"Apply Least Privilege to {source}",
                    "description": (
                        f"Role '{source}' has direct access to sensitive "
                        f"resource '{target}' (sensitivity: {resource.get('sensitivity')}). "
                        f"First, enumerate the role's attached and inline policies to identify "
                        f"the overly permissive policy. Then detach it and replace it with scoped permissions."
                    ),
                    "aws_cli": (
                        f"# 1. Find the overly permissive policy (attached and inline)\n"
                        f"aws iam list-attached-role-policies --role-name {source}\n"
                        f"aws iam list-role-policies --role-name {source}\n"
                        f"aws iam get-role-policy --role-name {source} --policy-name {{policy_name}}\n\n"
                        f"# 2. Detach or delete it (replace placeholders with actual names/ARNs)\n"
                        f"aws iam detach-role-policy --role-name {source} \\\n"
                        f"  --policy-arn {{policy_arn}}\n"
                        f"# OR for inline policies:\n"
                        f"aws iam delete-role-policy --role-name {source} \\\n"
                        f"  --policy-name {{policy_name}}\n\n"
                        f"# 3. Attach a scoped policy instead (example pattern)\n"
                        f"aws iam attach-role-policy --role-name {source} \\\n"
                        f"  --policy-arn arn:aws:iam::<account-id>:policy/{source}-ScopedPolicy"
                    ),
                    "impact": f"Reduces blast radius of {source} compromise",
                })

            elif rel_type == "ASSIGNED":
                recommendations.append({
                    "priority": "MEDIUM",
                    "title": f"Review user-to-role assignment: {source} → {target}",
                    "description": (
                        f"User '{source}' is directly assigned to role '{target}'. "
                        f"Verify this assignment follows the principle of least privilege. "
                        f"Consider using temporary credentials or session policies instead."
                    ),
                    "aws_cli": (
                        f"# Review current permissions\n"
                        f"aws iam list-attached-role-policies --role-name {target}\n"
                        f"aws iam list-role-policies --role-name {target}"
                    ),
                    "impact": f"Ensure {source} only has necessary permissions via {target}",
                })

    # Deduplicate and sort by priority
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    recommendations.sort(key=lambda r: priority_order.get(r["priority"], 99))

    return {
        "user": user,
        "total_issues": len(paths),
        "recommendations": recommendations,
        "weakest_edge": weakest_edge,
        "attack_path": [n["name"] for n in shortest["nodes"]] if shortest and "nodes" in shortest else [],
    }


def _find_weakest_edge(path: dict) -> dict | None:
    """Identify the single edge whose removal would break the path.

    Heuristic: prefer removing `ASSUME` edges (they are misconfigurations)
    over `ASSIGNED` edges (those are intentional).  Among `ASSUME` edges,
    pick the one closest to the sensitive resource (deeper in the chain).
    """
    chain = [n["name"] for n in path["nodes"]] if "nodes" in path and path["nodes"] and isinstance(path["nodes"][0], dict) else path.get("chain", [])
    rels = path.get("edges", path.get("relationships", []))

    if not rels:
        return None

    # Prefer ASSUME edges — they represent the actual misconfig
    assume_edges = [
        (i, rels[i]) for i in range(len(rels)) if rels[i] == "ASSUME"
    ]

    if assume_edges:
        # Pick the ASSUME closest to the resource (last in chain)
        idx, rel_type = assume_edges[-1]
    else:
        # Fallback: pick the last edge
        idx = len(rels) - 1
        rel_type = rels[idx]

    return {
        "source": chain[idx] if idx < len(chain) else "?",
        "target": chain[idx + 1] if idx + 1 < len(chain) else "?",
        "type": rel_type,
        "position": idx + 1,
        "total_hops": len(rels),
    }


def _generate_fix_command(edge: dict) -> str:
    """Generate a specific AWS CLI command to fix the weakest edge."""
    if edge["type"] == "ASSUME":
        return (
            f"# Remove the trust relationship allowing {edge['source']} to assume {edge['target']}\n"
            f"# Step 1: Get current trust policy\n"
            f"aws iam get-role --role-name {edge['target']} --query 'Role.AssumeRolePolicyDocument'\n\n"
            f"# Step 2: Edit the policy to remove {edge['source']} from Principal\n"
            f"# Step 3: Update the trust policy\n"
            f"aws iam update-assume-role-policy --role-name {edge['target']} \\\n"
            f"  --policy-document file://fixed-trust-policy.json"
        )
    elif edge["type"] == "ACCESS":
        return (
            f"# 1. Identify which policy grants access\n"
            f"aws iam list-attached-role-policies --role-name {edge['source']}\n"
            f"aws iam list-role-policies --role-name {edge['source']}\n\n"
            f"# 2. Detach or delete the overly permissive policy from {edge['source']}\n"
            f"aws iam detach-role-policy --role-name {edge['source']} \\\n"
            f"  --policy-arn {{policy_arn}}\n"
            f"# OR for inline policies:\n"
            f"aws iam delete-role-policy --role-name {edge['source']} \\\n"
            f"  --policy-name {{policy_name}}\n\n"
            f"# 3. Attach a replacement managed policy or apply a scoped inline policy\n"
            f"aws iam attach-role-policy --role-name {edge['source']} \\\n"
            f"  --policy-arn {{replacement_policy_arn}}"
        )
    else:
        return f"# Review and restrict the {edge['type']} relationship between {edge['source']} and {edge['target']}"
