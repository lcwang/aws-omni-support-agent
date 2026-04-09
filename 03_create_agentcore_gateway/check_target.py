import boto3
client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
r = client.get_gateway_target(gatewayIdentifier="gateway-support-xosfk0wt5b", targetId="N1US1ZRO1N")
print("Status:", r["status"])
print("Name:", r["name"])
