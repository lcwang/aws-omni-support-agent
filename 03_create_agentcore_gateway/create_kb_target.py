import boto3

client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")

response = client.create_gateway_target(
    gatewayIdentifier="gateway-support-xosfk0wt5b",
    name="kb-aws",
    description="A managed remote MCP server offering documentation, code samples, SOPs, AWS API regional availability info, and official AWS content.",
    targetConfiguration={
        "mcp": {
            "mcpRemoteServer": {
                "endpointUrl": "arn:aws:bedrock-agentcore:us-east-1:aws:managed-mcp-server/aws-knowledge-mcp-server",
            }
        }
    },
    credentialProviderConfigurations=[
        {
            "credentialProviderType": "GATEWAY_IAM_ROLE"
        }
    ]
)

print("AWS Knowledge MCP Server target created!")
print(f"Target ID: {response.get('targetId', 'N/A')}")
print(f"Status: {response.get('status', 'N/A')}")
