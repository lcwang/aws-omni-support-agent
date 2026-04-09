import boto3, json

aoss = boto3.client("opensearchserverless", region_name="us-east-1")
ACCOUNT_ID = "985539765717"
AGENT_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/AmazonBedrockAgentCoreSDKRuntime-us-east-1-295f81767d"

# List all access policies and update each one that matches
policies = aoss.list_access_policies(type="data")
for p in policies.get("accessPolicySummaries", []):
    if "bedrock-sample-rag-ap" not in p["name"]:
        continue

    detail = aoss.get_access_policy(name=p["name"], type="data")
    policy_doc = detail["accessPolicyDetail"]["policy"]

    # policy_doc might be a list already or a string
    if isinstance(policy_doc, str):
        policy_doc = json.loads(policy_doc)

    principals = policy_doc[0].get("Principal", [])
    if AGENT_ROLE_ARN in principals:
        print(f"  {p['name']}: Agent role already present, skipping")
        continue

    principals.append(AGENT_ROLE_ARN)
    policy_doc[0]["Principal"] = principals

    aoss.update_access_policy(
        name=p["name"],
        type="data",
        policyVersion=detail["accessPolicyDetail"]["policyVersion"],
        policy=json.dumps(policy_doc)
    )
    print(f"  ✅ {p['name']}: Added Agent role")

print("\nDone! Wait ~60 seconds for changes to propagate, then retry your query.")
