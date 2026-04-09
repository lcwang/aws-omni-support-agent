import os, json, boto3

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("target_config.json") as f:
    raw_config = json.load(f)

# API 要求的结构是 targetConfiguration.mcp.lambda，不是 lambdaTarget
lambda_config = raw_config["lambdaTarget"]
target_configuration = {
    "mcp": {
        "lambda": {
            "lambdaArn": lambda_config["lambdaArn"],
            "toolSchema": lambda_config["toolSchema"]
        }
    }
}

client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")

response = client.create_gateway_target(
    gatewayIdentifier="gateway-support-xosfk0wt5b",
    name="support-case",
    description="AWS Support Case management tools via Lambda",
    targetConfiguration=target_configuration,
    credentialProviderConfigurations=[
        {
            "credentialProviderType": "GATEWAY_IAM_ROLE"
        }
    ]
)

print("Target created successfully!")
print(f"Target ID: {response.get('targetId', 'N/A')}")
print(f"Status: {response.get('status', 'N/A')}")
