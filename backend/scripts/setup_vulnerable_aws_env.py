import boto3
import json
import logging
import time
import os
import sys

def wait_and_create_role(iam, role_name, trust_doc):
    for i in range(5):
        try:
            iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_doc))
            print(f"     ✅ Created {role_name}.")
            time.sleep(10) # Wait for role to propagate before next hop can reference it
            return
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"     ✅ {role_name} already exists. Updating trust policy...")
            try:
                iam.update_assume_role_policy(RoleName=role_name, PolicyDocument=json.dumps(trust_doc))
            except Exception as e:
                print(f"     ⚠️ Could not update trust policy for {role_name}: {e}")
            return
        except Exception as e:
            if "Invalid principal" in str(e):
                print(f"     ⏳ Principal not yet propagated. Retrying in 10s... ({i+1}/5)")
                time.sleep(10)
            else:
                print(f"     ❌ Error creating {role_name}: {e}")
                raise

    raise TimeoutError(f"Role {role_name} creation failed after retries due to principal non-propagation.")

def setup_vulnerable_aws_env():
    """Generates a real attack path inside the AWS account."""
    if os.environ.get("ALLOW_MUTATE_AWS", "").lower() != "true":
        print("⚠️ ABORTING: AWS mutation requires explicit opt-in.")
        print("Run this script with the environment variable ALLOW_MUTATE_AWS=true:")
        print("    ALLOW_MUTATE_AWS=true python setup_vulnerable_aws_env.py")
        sys.exit(1)

    iam = boto3.client('iam')
    sts = boto3.client("sts")
    try:
        account_id = sts.get_caller_identity()["Account"]
    except Exception as e:
        print(f"⚠️ STS Caller identity failed: {e}")
        sys.exit(1)
    
    print("Creating a Vulnerable AWS IAM Graph for the Hackathon Demo...")

    # 1. Create Intern User
    print("  -> Creating User: 'Intern_A'")
    try:
        iam.create_user(UserName='Intern_A')
        print("     Waiting 15 seconds for IAM user to propagate globally in AWS...")
        time.sleep(15)
    except iam.exceptions.EntityAlreadyExistsException:
        print("     ✅ User already exists.")
    except Exception as e:
        print(f"     ❌ Could not create user: {e}")

    # 2. Create InternRole
    print("  -> Creating Role: 'InternRole' (Can be assumed by Intern_A)")
    trust_intern = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"AWS": f"arn:aws:iam::{account_id}:user/Intern_A"}, "Action": "sts:AssumeRole"}]
    }
    wait_and_create_role(iam, 'InternRole', trust_intern)

    # 3. Create DevRole
    print("  -> Creating Role: 'DevRole' (Can be assumed by InternRole)")
    trust_dev = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"AWS": f"arn:aws:iam::{account_id}:role/InternRole"}, "Action": "sts:AssumeRole"}]
    }
    wait_and_create_role(iam, 'DevRole', trust_dev)

    # 4. Create AdminRole
    print("  -> Creating Role: 'AdminRole' (Can be assumed by DevRole)")
    trust_admin = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"AWS": f"arn:aws:iam::{account_id}:role/DevRole"}, "Action": "sts:AssumeRole"}]
    }
    wait_and_create_role(iam, 'AdminRole', trust_admin)

    # 5. Attach Admin Policy to AdminRole (Simulating the final crown jewel target)
    print("  -> Attaching AdministratorAccess policy to AdminRole")
    try:
        iam.attach_role_policy(RoleName='AdminRole', PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess')
    except Exception as e:
        print(f"     ⚠️ Could not attach Admin policy: {e}")

    print("\n✅ Success! A live privilege escalation chain has been deployed to AWS.")
    print("Path: Intern_A -> InternRole -> DevRole -> AdminRole -> AdministratorAccess")
    print("Go to the dashboard and click 'AWS IAM Data' to visualize it in Neo4j!")

if __name__ == "__main__":
    setup_vulnerable_aws_env()
