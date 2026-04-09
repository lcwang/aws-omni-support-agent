import boto3, json

REGION = "us-east-1"
KB_ID = "GZDVPKC7AU"

# 1. Check KB status
print("=== Knowledge Base Status ===")
bedrock_agent = boto3.client("bedrock-agent", region_name=REGION)
kb = bedrock_agent.get_knowledge_base(knowledgeBaseId=KB_ID)
kb_detail = kb["knowledgeBase"]
print(f"  Name: {kb_detail['name']}")
print(f"  Status: {kb_detail['status']}")
print(f"  Role ARN: {kb_detail['roleArn']}")
print(f"  Storage: {json.dumps(kb_detail.get('storageConfiguration', {}), indent=2, default=str)[:500]}")

# 2. Test retrieve directly with current credentials
print("\n=== Testing Retrieve API ===")
bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
try:
    resp = bedrock_runtime.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": "EC2 M5 instance memory"},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 3
            }
        }
    )
    results = resp.get("retrievalResults", [])
    print(f"  ✅ Retrieve succeeded! Got {len(results)} results")
    for i, r in enumerate(results):
        text = r.get("content", {}).get("text", "")[:100]
        print(f"  Result {i+1}: {text}...")
except Exception as e:
    print(f"  ❌ Retrieve failed: {e}")

# 3. Check what role the Agent Runtime is using
print("\n=== Agent Execution Role Permissions ===")
iam = boto3.client("iam")
role_name = "AmazonBedrockAgentCoreSDKRuntime-us-east-1-295f81767d"
try:
    policies = iam.list_role_policies(RoleName=role_name)
    print(f"  Inline policies: {policies['PolicyNames']}")
    for pname in policies["PolicyNames"]:
        p = iam.get_role_policy(RoleName=role_name, PolicyName=pname)
        print(f"\n  Policy '{pname}':")
        print(f"  {json.dumps(p['PolicyDocument'], indent=2)[:500]}")
except Exception as e:
    print(f"  Error: {e}")
