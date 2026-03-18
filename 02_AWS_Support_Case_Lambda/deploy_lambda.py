#!/usr/bin/env python3
"""
Lambda 部署脚本
使用 boto3 直接部署 Lambda 函数到 AWS
"""

import boto3
import zipfile
import os
import json
from pathlib import Path

# 配置
LAMBDA_FUNCTION_NAME = 'aws-support-tools-lambda'
LAMBDA_ROLE_NAME = 'aws-support-lambda-execution-role'
LAMBDA_RUNTIME = 'python3.11'
LAMBDA_HANDLER = 'lambda_handler.lambda_handler'
LAMBDA_TIMEOUT = 60  # 秒
LAMBDA_MEMORY = 512  # MB
REGION = 'us-east-1'

def create_deployment_package():
    """创建 Lambda 部署包"""
    print("[1/6] Creating Lambda deployment package...")

    zip_path = '/tmp/lambda_deployment.zip'

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 添加 Lambda handler
        zipf.write('lambda_handler.py', 'lambda_handler.py')

    print(f"✓ Deployment package created: {zip_path}")
    return zip_path


def create_iam_role(iam_client):
    """创建 IAM Role"""
    print("[2/6] Creating IAM role...")

    # Trust policy
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        # 创建 Role
        response = iam_client.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Execution role for AWS Support Lambda function'
        )
        role_arn = response['Role']['Arn']
        print(f"✓ Created IAM role: {role_arn}")

        # 附加权限策略
        with open('iam_policy.json', 'r') as f:
            policy_document = f.read()

        iam_client.put_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyName='AWSSupportLambdaPolicy',
            PolicyDocument=policy_document
        )
        print(f"✓ Attached policy to role")

        # 等待角色生效
        import time
        print("  Waiting for IAM role to propagate...")
        time.sleep(10)

        return role_arn

    except iam_client.exceptions.EntityAlreadyExistsException:
        print("  Role already exists, retrieving ARN...")
        response = iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)
        return response['Role']['Arn']


def create_or_update_lambda(lambda_client, role_arn, zip_path):
    """创建或更新 Lambda 函数"""
    print("[3/6] Creating/Updating Lambda function...")

    with open(zip_path, 'rb') as f:
        zip_content = f.read()

    try:
        # 尝试创建新函数
        response = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime=LAMBDA_RUNTIME,
            Role=role_arn,
            Handler=LAMBDA_HANDLER,
            Code={'ZipFile': zip_content},
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY,
            Description='AWS Support API Tools for AgentCore Gateway'
        )
        function_arn = response['FunctionArn']
        print(f"✓ Created Lambda function: {function_arn}")

    except lambda_client.exceptions.ResourceConflictException:
        print("  Function already exists, updating code...")
        lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=zip_content
        )

        # 获取函数 ARN
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        function_arn = response['Configuration']['FunctionArn']
        print(f"✓ Updated Lambda function: {function_arn}")

    return function_arn


def test_lambda(lambda_client):
    """测试 Lambda 函数"""
    print("[4/6] Testing Lambda function...")

    test_event = {
        "tool_name": "describe_severity_levels",
        "parameters": {
            "language": "en"
        }
    }

    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )

        result = json.loads(response['Payload'].read())
        print(f"✓ Lambda test successful:")
        print(f"  Status: {result['statusCode']}")
        print(f"  Body: {json.dumps(json.loads(result['body']), indent=2)}")

    except Exception as e:
        print(f"✗ Lambda test failed: {str(e)}")


def add_gateway_permission(lambda_client, function_arn, account_id):
    """添加 AgentCore Gateway 调用权限"""
    print("[5/6] Adding AgentCore Gateway permission...")

    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId='AllowAgentCoreGatewayInvoke',
            Action='lambda:InvokeFunction',
            Principal='bedrock.amazonaws.com',
            SourceArn=f'arn:aws:bedrock:{REGION}:{account_id}:*'
        )
        print(f"✓ Added permission for AgentCore Gateway")
    except lambda_client.exceptions.ResourceConflictException:
        print(f"  Permission already exists")


def print_summary(function_arn):
    """打印部署摘要"""
    print("\n" + "="*60)
    print("[6/6] Deployment Summary")
    print("="*60)
    print(f"Lambda Function ARN: {function_arn}")
    print(f"Function Name: {LAMBDA_FUNCTION_NAME}")
    print(f"Region: {REGION}")
    print("\nAvailable Tools:")
    tools = [
        'create_support_case',
        'describe_support_cases',
        'add_communication_to_case',
        'resolve_support_case',
        'describe_services',
        'describe_severity_levels',
        'add_attachments_to_set'
    ]
    for tool in tools:
        print(f"  - {tool}")
    print("\n" + "="*60)
    print("Next Steps:")
    print("1. Copy the Lambda ARN above")
    print("2. Add this Lambda as a target in your AgentCore Gateway")
    print("3. Update your Agent code to use Lambda tools (see updated_agent.py)")
    print("="*60)


def main():
    """主部署流程"""
    print("\n🚀 AWS Support Lambda Deployment Script\n")

    # 切换到 Lambda 目录
    os.chdir(Path(__file__).parent)

    # 初始化 AWS 客户端
    session = boto3.Session(region_name=REGION)
    sts_client = session.client('sts')
    account_id = sts_client.get_caller_identity()['Account']

    iam_client = session.client('iam')
    lambda_client = session.client('lambda')

    try:
        # 创建部署包
        zip_path = create_deployment_package()

        # 创建 IAM Role
        role_arn = create_iam_role(iam_client)

        # 创建/更新 Lambda
        function_arn = create_or_update_lambda(lambda_client, role_arn, zip_path)

        # 测试 Lambda
        test_lambda(lambda_client)

        # 添加 Gateway 权限
        add_gateway_permission(lambda_client, function_arn, account_id)

        # 打印摘要
        print_summary(function_arn)

        print("\n✅ Deployment completed successfully!\n")

    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}\n")
        raise


if __name__ == '__main__':
    main()
