import boto3
import json
from pathlib import Path

iam = boto3.client("iam")

data = {
    "users": [],
    "roles": [],
    "policies": [],
    "user_roles": [],
    "role_policies": []
}

policies_set = set()

# Get users
user_paginator = iam.get_paginator('list_users')
for page in user_paginator.paginate():
    for user in page["Users"]:
        username = user["UserName"]
        data["users"].append(username)

        for group_page in iam.get_paginator('list_groups_for_user').paginate(UserName=username):
            for g in group_page["Groups"]:
                data["user_roles"].append({
                    "user": username,
                    "role": g["GroupName"]
                })

# Get roles
role_paginator = iam.get_paginator('list_roles')
for page in role_paginator.paginate():
    for role in page["Roles"]:
        rolename = role["RoleName"]
        data["roles"].append(rolename)

        for policy_page in iam.get_paginator('list_attached_role_policies').paginate(RoleName=rolename):
            for p in policy_page["AttachedPolicies"]:
                policy_name = p["PolicyName"]
                policies_set.add(policy_name)
                data["role_policies"].append({
                    "role": rolename,
                    "policy": policy_name
                })

data["policies"] = list(policies_set)

output_file = Path(__file__).resolve().parent.parent.parent / "dataset" / "aws_iam_data.json"
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, "w") as f:
    json.dump(data, f, indent=2)

print("IAM graph data exported to", output_file)