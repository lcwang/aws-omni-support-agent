import boto3

ssm = boto3.client("ssm", region_name="us-east-1")
gateway_url = "https://gateway-support-xosfk0wt5b.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

response = ssm.put_parameter(
    Name="/support/agentgateway/aws_support_gateway",
    Value=gateway_url,
    Type="String",
    Overwrite=True
)
print(f"Gateway URL stored in SSM: /support/agentgateway/aws_support_gateway")
print(f"URL: {gateway_url}")
