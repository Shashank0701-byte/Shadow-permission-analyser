import boto3
import json

iam = boto3.client("iam")

data = {
    "users": [],
    "roles": [],
    "policies": [],
    "user_roles": [],
    "role_policies": []
}

# Get users
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

# Get roles
roles = iam.list_roles()["Roles"]

for role in roles:
    rolename = role["RoleName"]
    data["roles"].append(rolename)

    policies = iam.list_attached_role_policies(RoleName=rolename)["AttachedPolicies"]

    for p in policies:
        data["role_policies"].append({
            "role": rolename,
            "policy": p["PolicyName"]
        })

with open("../dataset/aws_iam_data.json", "w") as f:
    json.dump(data, f, indent=2)

print("IAM graph data exported")