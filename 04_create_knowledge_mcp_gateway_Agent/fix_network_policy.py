import boto3, json

aoss = boto3.client("opensearchserverless", region_name="us-east-1")
POLICY_NAME = "bedrock-sample-rag-np-1170134-f"

detail = aoss.get_security_policy(name=POLICY_NAME, type="network")
version = detail["securityPolicyDetail"]["policyVersion"]

new_policy = [
    {
        "Rules": [
            {
                "Resource": ["collection/bedrock-sample-rag-1170134-f"],
                "ResourceType": "collection"
            }
        ],
        "AllowFromPublic": True
    }
]

aoss.update_security_policy(
    name=POLICY_NAME,
    type="network",
    policyVersion=version,
    policy=json.dumps(new_policy)
)
print("✅ Network policy updated: AllowFromPublic = True")
