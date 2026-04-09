import boto3, json

aoss = boto3.client("opensearchserverless", region_name="us-east-1")
sts = boto3.client("sts")

ACCOUNT_ID = "985539765717"
CALLER_ARN = sts.get_caller_identity()["Arn"]
AGENT_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/AmazonBedrockAgentCoreSDKRuntime-us-east-1-295f81767d"
KB_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/AmazonBedrockExecutionRoleForKnowledgeBase_1170134-f"

print(f"Caller: {CALLER_ARN}")
print(f"Agent Role: {AGENT_ROLE_ARN}")
print(f"KB Role: {KB_ROLE_ARN}")

# Check all access policies
policies = aoss.list_access_policies(type="data")
for p in policies.get("accessPolicySummaries", []):
    detail = aoss.get_access_policy(name=p["name"], type="data")
    policy_doc = detail["accessPolicyDetail"]["policy"]
    if isinstance(policy_doc, str):
        policy_doc = json.loads(policy_doc)

    principals = policy_doc[0].get("Principal", [])
    print(f"\n--- {p['name']} ---")
    print(f"  Principals: {principals}")
    print(f"  Rules: {[r.get('Resource', []) for r in policy_doc[0].get('Rules', [])]}")

    # Check if this policy covers our collection
    resources = []
    for rule in policy_doc[0].get("Rules", []):
        resources.extend(rule.get("Resource", []))

    # Find the policy that matches our KB's collection
    if any("xggorutm23tchjsravz0" in r or "1170134" in r for r in resources):
        print(f"  >>> This is our KB's policy!")

        # Ensure all needed principals are present
        changed = False
        for arn in [CALLER_ARN, AGENT_ROLE_ARN, KB_ROLE_ARN]:
            if arn not in principals:
                principals.append(arn)
                changed = True
                print(f"  + Adding: {arn}")

        if changed:
            policy_doc[0]["Principal"] = principals
            aoss.update_access_policy(
                name=p["name"],
                type="data",
                policyVersion=detail["accessPolicyDetail"]["policyVersion"],
                policy=json.dumps(policy_doc)
            )
            print(f"  ✅ Policy updated!")
        else:
            print(f"  All principals already present")

print("\nDone. Wait 60s then retry.")
