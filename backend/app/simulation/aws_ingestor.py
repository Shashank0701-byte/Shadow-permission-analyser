import boto3
import json
import logging

logger = logging.getLogger(__name__)

def fetch_live_aws_iam_data() -> dict:
    """Fetch live IAM data from the configured AWS account using boto3."""
    logger.info("Initializing boto3 IAM client...")
    iam = boto3.client("iam")

    data = {
        "users": [],
        "roles": [],
        "policies": [],
        "user_roles": [],
        "role_policies": [],
        "assume": [],
        "assignments": [],
        "resources": [],
        "permissions": []
    }

    # Get users
    try:
        logger.info("Fetching AWS IAM Users...")
        users = iam.list_users()["Users"]
        
        for user in users:
            username = user["UserName"]
            data["users"].append(username)

            groups = iam.list_groups_for_user(UserName=username)["Groups"]
            for g in groups:
                data["user_roles"].append({
                    "user": username,
                    "role": g["GroupName"]
                })
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise e

    # Get roles
    try:
        logger.info("Fetching AWS IAM Roles...")
        # Filtering down to roles that might be relevant, or just get all
        # To avoid massive AWS managed role lists, sometimes we filter, 
        # but list_roles gets them all. Let's paginate or just get the first batch for the hackathon
        paginator = iam.get_paginator('list_roles')
        roles = []
        for response in paginator.paginate():
            roles.extend(response["Roles"])
            if len(roles) > 100:  # Cap at 100 for graph performance during hackathon demo
                break
                
        for role in roles[:100]:
            rolename = role["RoleName"]
            data["roles"].append(rolename)

            policies = iam.list_attached_role_policies(RoleName=rolename)["AttachedPolicies"]

            for p in policies:
                data["role_policies"].append({
                    "role": rolename,
                    "policy": p["PolicyName"]
                })
                # Add policy to policies list if not already there
                if p["PolicyName"] not in data["policies"]:
                    data["policies"].append(p["PolicyName"])
                
                # Hackathon Demo Sugar: Assume any attached policy with a sensitive sounding name is a Resource!
                policy_name = p["PolicyName"]
                if "Admin" in policy_name or "DB" in policy_name or "Production" in policy_name:
                    res_name = f"Resource_{policy_name}"
                    if res_name not in [r["name"] for r in data.get("resources", [])]:
                        data["resources"].append({"name": res_name, "sensitivity": 5})
                    data["permissions"].append({"role": rolename, "resource": res_name})

            # ── Parse AssumeRole Trust Policies (This builds the Vulnerability Map!) ──
            trust_doc = role.get("AssumeRolePolicyDocument", {})
            for statement in trust_doc.get("Statement", []):
                if statement.get("Effect") == "Allow" and statement.get("Action") == "sts:AssumeRole":
                    principal = statement.get("Principal", {}).get("AWS", [])
                    
                    if isinstance(principal, str):
                        principals = [principal]
                    else:
                        principals = principal
                        
                    for p_arn in principals:
                        if isinstance(p_arn, str) and ":" in p_arn:
                            # It's an ARN like arn:aws:iam::12345:user/Intern_A
                            source_name = p_arn.split("/")[-1]
                            
                            if ":user/" in p_arn:
                                data["assignments"].append((source_name, rolename))
                            elif ":role/" in p_arn:
                                data["assume"].append((source_name, rolename))
                    
    except Exception as e:
        logger.error(f"Error fetching roles: {e}")
        raise e

    logger.info("Successfully fetched live AWS IAM data.")
    return data
