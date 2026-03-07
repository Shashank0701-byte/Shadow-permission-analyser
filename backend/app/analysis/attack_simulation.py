"""Attack simulation — generates step-by-step AWS CLI commands.

Given an escalation path like `Intern_A → InternRole → DevRole → AdminRole`,
this module generates the exact sequence of `aws sts assume-role` commands
an attacker would execute to exploit the chain.

Public API
----------
``generate_attack_steps(user)``
    Returns ordered attack steps with CLI commands for the weakest path.
"""

from app.graph.queries import get_shortest_escalation_path
from app.core.database import get_session


def generate_attack_steps(user: str) -> dict:
    """Generate step-by-step attack simulation for *user*.

    Returns
    -------
    dict
        ``user``
            The starting identity.
        ``steps``
            Ordered list of attack steps with CLI commands.
        ``total_steps``
            Number of hops in the attack.
        ``final_access``
            The ultimate resource/privilege gained.
    """
    path = get_shortest_escalation_path(user)

    if not path:
        return {
            "user": user,
            "steps": [],
            "total_steps": 0,
            "final_access": None,
            "message": f"No escalation path found for user '{user}'.",
        }

    # Fetch the account ID from the graph for realistic ARNs
    session = get_session()
    # Use a placeholder account ID for display
    account_id = "XXXXXXXXXXXX"

    steps = []
    # The path object has 'nodes' (list of {id, label, name, sensitivity})
    # and 'edges' (list of relationship type strings)
    path_nodes = path["nodes"]
    relationships = path["edges"]
    chain = [n["name"] for n in path_nodes]

    for i in range(len(relationships)):
        source = chain[i]
        target = chain[i + 1]
        rel_type = relationships[i]

        step_num = i + 1

        if rel_type == "ASSIGNED":
            steps.append({
                "step": step_num,
                "action": "Initial Access",
                "description": f"Attacker compromises user '{source}' credentials (phishing, leaked keys, etc.)",
                "cli_command": f"aws sts get-caller-identity\n# Returns: arn:aws:iam::{account_id}:user/{source}",
                "risk": "Entry point — attacker now has user-level access",
                "technique": "MITRE ATT&CK: T1078 (Valid Accounts)",
            })

        elif rel_type == "ASSUME":
            steps.append({
                "step": step_num,
                "action": "Privilege Escalation via Role Assumption",
                "description": f"Attacker assumes role '{target}' from '{source}' using STS",
                "cli_command": (
                    f"aws sts assume-role \\\n"
                    f"  --role-arn arn:aws:iam::{account_id}:role/{target} \\\n"
                    f"  --role-session-name attack-session-{step_num}\n\n"
                    f"# Export the returned credentials:\n"
                    f"export AWS_ACCESS_KEY_ID=<AccessKeyId>\n"
                    f"export AWS_SECRET_ACCESS_KEY=<SecretAccessKey>\n"
                    f"export AWS_SESSION_TOKEN=<SessionToken>"
                ),
                "risk": f"Attacker now operates as '{target}' with elevated privileges",
                "technique": "MITRE ATT&CK: T1098.001 (Account Manipulation: Additional Cloud Credentials)",
            })

        elif rel_type == "ACCESS":
            steps.append({
                "step": step_num,
                "action": "Resource Access — Mission Complete",
                "description": f"Attacker accesses sensitive resource '{target}' via role '{source}'",
                "cli_command": (
                    f"# With '{source}' credentials, attacker can now:\n"
                    f"aws iam list-attached-role-policies --role-name {source}\n"
                    f"aws s3 ls  # List all S3 buckets\n"
                    f"aws rds describe-db-instances  # Find databases\n"
                    f"aws secretsmanager list-secrets  # Steal secrets"
                ),
                "risk": f"CRITICAL — Full access to '{target}' achieved",
                "technique": "MITRE ATT&CK: T1530 (Data from Cloud Storage)",
            })

        elif rel_type == "HAS_POLICY":
            steps.append({
                "step": step_num,
                "action": "Policy Attachment",
                "description": f"Role '{source}' has policy '{target}' attached",
                "cli_command": f"aws iam list-attached-role-policies --role-name {source}",
                "risk": f"Policy '{target}' grants additional permissions",
                "technique": "MITRE ATT&CK: T1484 (Domain Policy Modification)",
            })

        else:
            steps.append({
                "step": step_num,
                "action": f"Traversal ({rel_type})",
                "description": f"'{source}' → '{target}' via {rel_type}",
                "cli_command": f"# Relationship: {rel_type}",
                "risk": "Intermediate hop in the escalation chain",
                "technique": "N/A",
            })

    return {
        "user": user,
        "steps": steps,
        "total_steps": len(steps),
        "final_access": chain[-1] if chain else None,
        "attack_path": " → ".join(chain),
    }
