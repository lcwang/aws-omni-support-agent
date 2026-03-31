import boto3
import json
import pickle
import os
import argparse
from boto3.session import Session


def test_invoke_agent(prompt_text=None, iam_user=None):
    """Test the deployed support case agent by invoking it with a sample prompt

    Args:
        prompt_text: 测试提示词
        iam_user: IAM 用户名（可选，用于 RBAC 测试）
    """

    # 默认测试提示词
    if not prompt_text:
        prompt_text = "帮我查看一下过去三个月的case并总结给我"

    def invoke_agent(prompt_text, iam_user=None):
        boto_session = Session()
        #REGION = boto_session.region_name
        REGION = 'us-east-1'

        # Get agent ARN from launch_result.pkl or environment variable
        try:
            with open('launch_result.pkl', 'rb') as f:
                launch_result = pickle.load(f)
            agent_arn = launch_result.agent_arn
        except FileNotFoundError:
            # Fallback to environment variable
            agent_arn = os.environ.get('AGENT_ARN')
            if not agent_arn:
                raise ValueError(
                    "Agent ARN not found. Please either:\n"
                    "1. Run deployment to generate launch_result.pkl, or\n"
                    "2. Set AGENT_ARN environment variable\n"
                    "Example: export AGENT_ARN='arn:aws:bedrock-agentcore:REGION:ACCOUNT:runtime/AGENT_ID'"
                )

        print(f"Using agent ARN: {agent_arn}")

        agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)

        # 构建 payload
        payload = {"prompt": prompt_text}

        # 如果提供了 iam_user，添加到 payload
        if iam_user:
            payload["_user_context"] = {"iam_user": iam_user}
            print(f"👤 使用用户身份: {iam_user}")

        try:
            boto3_response = agentcore_client.invoke_agent_runtime(
                agentRuntimeArn=agent_arn,
                qualifier="DEFAULT",
                payload=json.dumps(payload)
            )

            print(f"Response status: {boto3_response['statusCode']}")
            print(f"Content type: {boto3_response.get('contentType', 'N/A')}")

            # Handle streaming response
            if "text/event-stream" in boto3_response.get("contentType", ""):
                print("Agent response:")
                try:
                    response_body = boto3_response["response"].read()
                    # Parse and clean the streaming data
                    lines = response_body.decode('utf-8').split('\n')
                    content = []
                    for line in lines:
                        if line.startswith('data: '):
                            data = line[6:].strip('"')
                            if data and data != '\\n':
                                content.append(data)

                    full_response = ''.join(content).replace('\\n', '\n')
                    print(full_response)
                except Exception as e:
                    print(f"Error reading response: {e}")
            else:
                print("Non-streaming response")

        except Exception as e:
            print(f"Error invoking agent: {e}")
            return False

        return True

    print(f"Testing with prompt: {prompt_text}")
    success = invoke_agent(prompt_text, iam_user)

    if success:
        print("✅ Test completed successfully")
    else:
        print("❌ Test failed")

    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='测试 AWS Support Agent')
    parser.add_argument('--prompt', type=str, help='自定义测试提示词')
    parser.add_argument('--iam-user', type=str, help='IAM 用户名（用于 RBAC 测试）')

    args = parser.parse_args()

    test_invoke_agent(
        prompt_text=args.prompt,
        iam_user=args.iam_user
    )
