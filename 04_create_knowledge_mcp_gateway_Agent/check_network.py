import boto3, json

aoss = boto3.client("opensearchserverless", region_name="us-east-1")

# Check network policies
print("=== Network Policies ===")
np = aoss.list_security_policies(type="network")
for p in np.get("securityPolicySummaries", []):
    detail = aoss.get_security_policy(name=p["name"], type="network")
    policy = detail["securityPolicyDetail"]["policy"]
    if isinstance(policy, str):
        policy = json.loads(policy)
    print(f"\n{p['name']}:")
    print(f"  {json.dumps(policy, indent=2)}")

# Check collection status
print("\n=== Collections ===")
colls = aoss.list_collections()
for c in colls.get("collectionSummaries", []):
    print(f"  {c['name']}: {c['status']} (id: {c['id']})")

# Direct test: can we reach the collection endpoint?
print("\n=== Direct Retrieve Test ===")
bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
try:
    resp = bedrock_runtime.retrieve(
        knowledgeBaseId="GZDVPKC7AU",
        retrievalQuery={"text": "EC2"},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 1}}
    )
    print(f"  ✅ Success: {len(resp.get('retrievalResults', []))} results")
except Exception as e:
    print(f"  ❌ Failed: {e}")
