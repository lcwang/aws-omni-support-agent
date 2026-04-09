import boto3, json

iam = boto3.client("iam")
ROLE_NAME = "AmazonBedrockAgentCoreSDKRuntime-us-east-1-295f81767d"
ACCOUNT_ID = "985539765717"

policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "SSMGetParameter",
            "Effect": "Allow",
            "Action": "ssm:GetParameter",
            "Resource": f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/support/*"
        },
        {
            "Sid": "BedrockRetrieve",
            "Effect": "Allow",
            "Action": ["bedrock:Retrieve", "bedrock:InvokeModel"],
            "Resource": "*"
        },
        {
            "Sid": "InvokeGateway",
            "Effect": "Allow",
            "Action": "bedrock-agentcore:InvokeGateway",
            "Resource": f"arn:aws:bedrock-agentcore:us-east-1:{ACCOUNT_ID}:gateway/*"
        }
    ]
}

iam.put_role_policy(
    RoleName=ROLE_NAME,
    PolicyName="AgentCoreAdditionalPermissions",
    PolicyDocument=json.dumps(policy)
)
print("✅ Permissions granted to Agent execution role")
