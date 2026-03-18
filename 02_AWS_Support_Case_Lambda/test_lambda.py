#!/usr/bin/env python3
"""
Lambda 测试脚本
测试所有 7 个工具的功能
"""

import boto3
import json
from typing import Dict, Any

LAMBDA_FUNCTION_NAME = 'aws-support-tools-lambda'
REGION = 'us-east-1'


def invoke_lambda(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """调用 Lambda 函数"""
    lambda_client = boto3.client('lambda', region_name=REGION)

    event = {
        "tool_name": tool_name,
        "parameters": parameters
    }

    print(f"\n{'='*60}")
    print(f"Testing: {tool_name}")
    print(f"{'='*60}")
    print(f"Request: {json.dumps(event, indent=2)}")

    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        result = json.loads(response['Payload'].read())
        body = json.loads(result['body'])

        print(f"\nStatus Code: {result['statusCode']}")
        print(f"Response:\n{json.dumps(body, indent=2, default=str)}")

        if result['statusCode'] == 200:
            print("✅ Test PASSED")
        else:
            print("❌ Test FAILED")

        return body

    except Exception as e:
        print(f"❌ Test FAILED with exception: {str(e)}")
        return {"error": str(e)}


def test_describe_severity_levels():
    """测试 1: 获取严重级别列表"""
    return invoke_lambda(
        tool_name="describe_severity_levels",
        parameters={"language": "en"}
    )


def test_describe_services():
    """测试 2: 获取服务列表（仅EC2）"""
    return invoke_lambda(
        tool_name="describe_services",
        parameters={
            "service_code_list": ["amazon-elastic-compute-cloud-linux"],
            "language": "en"
        }
    )


def test_describe_cases():
    """测试 3: 查询最近的 case"""
    return invoke_lambda(
        tool_name="describe_support_cases",
        parameters={
            "include_resolved_cases": False,
            "include_communications": True,
            "max_results": 10
        }
    )


def test_create_case():
    """测试 4: 创建测试 case（需要真实的Support计划）"""
    print("\n⚠️  Skipping create_case test (requires manual confirmation)")
    return None

    return invoke_lambda(
        tool_name="create_support_case",
        parameters={
            "subject": "[TEST] Lambda Integration Test",
            "service_code": "amazon-elastic-compute-cloud-linux",
            "category_code": "using-aws",
            "severity_code": "low",
            "communication_body": "This is a test case created by Lambda integration test. Please ignore.",
            "language": "en",
            "issue_type": "technical"
        }
    )


def test_add_communication(case_id: str):
    """测试 5: 添加回复（需要真实的case_id）"""
    if not case_id:
        print("\n⏭️  Skipping add_communication test (no case_id)")
        return None

    return invoke_lambda(
        tool_name="add_communication_to_case",
        parameters={
            "case_id": case_id,
            "communication_body": "This is an additional test communication."
        }
    )


def test_resolve_case(case_id: str):
    """测试 6: 关闭 case（需要真实的case_id）"""
    if not case_id:
        print("\n⏭️  Skipping resolve_case test (no case_id)")
        return None

    print("\n⚠️  Skipping resolve_case test (requires manual confirmation)")
    return None

    return invoke_lambda(
        tool_name="resolve_support_case",
        parameters={"case_id": case_id}
    )


def test_add_attachments():
    """测试 7: 上传附件"""
    import base64

    # 创建一个测试文件内容
    test_content = "This is a test attachment file.\nLine 2\nLine 3"
    encoded_content = base64.b64encode(test_content.encode()).decode()

    return invoke_lambda(
        tool_name="add_attachments_to_set",
        parameters={
            "attachments": [
                {
                    "fileName": "test_attachment.txt",
                    "data": encoded_content
                }
            ]
        }
    )


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("AWS Support Lambda Integration Tests")
    print("="*60)

    # 测试 1: 获取严重级别
    test_describe_severity_levels()

    # 测试 2: 获取服务列表
    test_describe_services()

    # 测试 3: 查询 case
    cases_result = test_describe_cases()

    # 测试 4: 创建 case (可选)
    create_result = test_create_case()

    # 获取测试 case_id
    test_case_id = None
    if create_result and create_result.get('caseId'):
        test_case_id = create_result['caseId']
    elif cases_result and cases_result.get('cases'):
        # 使用第一个查询到的 case
        test_case_id = cases_result['cases'][0].get('caseId')

    # 测试 5: 添加回复
    test_add_communication(test_case_id)

    # 测试 6: 上传附件
    test_add_attachments()

    # 测试 7: 关闭 case (可选)
    test_resolve_case(test_case_id)

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == '__main__':
    main()
